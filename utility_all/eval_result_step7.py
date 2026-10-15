import re
import json
import numpy as np
import Levenshtein # 用于计算编辑距离 (CER)
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import os
from typing import List, Dict, Any
import pandas as pd
import sys
import argparse
from datetime import datetime 
import asyncio
import ast
# --- I. 辅助函数和解析函数 (与前文相同) ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(project_root,"src"))
from models.ocr_model.utils.hu_rec_qwen3VL_api import QWenInference_dect_rec_api
# 辅助函数：IoU (Intersection over Union)
def calculate_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    # ... (IoU 实现代码，与前文一致) ...
    x_start_A, y_start_A, x_end_A, y_end_A = boxA
    x_start_B, y_start_B, x_end_B, y_end_B = boxB
    x_inter_start = max(x_start_A, x_start_B)
    y_inter_start = max(y_start_A, y_start_B)
    x_inter_end = min(x_end_A, x_end_B)
    y_inter_end = min(y_end_A, y_end_B)
    inter_width = max(0, x_inter_end - x_inter_start)
    inter_height = max(0, y_inter_end - y_inter_start)
    inter_area = inter_width * inter_height
    area_A = (x_end_A - x_start_A) * (y_end_A - y_start_A)
    area_B = (x_end_B - x_start_B) * (y_end_B - y_start_B)
    union_area = area_A + area_B - inter_area
    return inter_area / union_area if union_area > 0 else 0.0

# 辅助函数：计算字符错误率 (CER)
def calculate_cer(reference: str, hypothesis: str) -> float:
    # ... (CER 实现代码，与前文一致) ...
    distance = Levenshtein.distance(reference, hypothesis)
    reference_length = len(reference)
    return distance / reference_length if reference_length > 0 else 1.0 if len(hypothesis) > 0 else 0.0

# 数据解析函数
def parse_assistant_content(content: str) -> List[Dict[str, Any]]:
    """解析模型输出的 assistant content 字符串，提取边界框、类别和识别内容。"""
    # ... (解析实现代码，与前文一致) ...
    parsed_items = []
    # 注意: 使用 $? 确保即使内容两侧没有 $ 也能匹配
    pattern = re.compile(
        r'<\|box_start\|>\((\d+),(\d+)\),\((\d+),(\d+)\)<\|box_end\|><\|object_ref_start\|>(\w+):\$?(.*?)\$?<\|object_ref_end\|>'
    )
    
    matches = pattern.findall(content)
    
    for match in matches:
        x1, y1, x2, y2, label_str, content_raw = match
        box = (int(x1), int(y1), int(x2), int(y2))
        
        # 清理内容中的转义字符
        cleaned_content = content_raw.strip().replace('\\\\', '\\')
        
        parsed_items.append({
            "box": box,
            "label_str": label_str,
            "content": cleaned_content,
        })
    
    return parsed_items

# --- II. 评估主函数 (与前文相同) ---


# 假设以下函数已在其他地方定义
# def calculate_iou(box1: List[int], box2: List[int]) -> float: ...
# def calculate_cer(gt_text: str, pred_text: str) -> float: ...
# def parse_assistant_content(content_str: str) -> List[Dict[str, Any]]: ...

def evaluate_ocr_multi_task(
    predictions_raw: List[Dict[str, Any]],
    ground_truths_raw: List[Dict[str, Any]],
    class_to_idx: Dict[str, int],
    iou_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    评估多任务OCR模型的性能，并统计每张图片在检测、分类、识别上的错误状态。
    """
    
    if len(predictions_raw) != len(ground_truths_raw):
        raise ValueError("预测和真实标签的样本数量不匹配。")
        
    total_samples = len(ground_truths_raw)
    
    # ------------------ 全局指标初始化 (与原有功能一致) ------------------
    total_cross_entropy_loss = 0.0
    total_gt_boxes = 0
    total_pred_boxes = 0
    true_positives = 0
    correct_classification = 0
    total_matched_instances = 0
    total_cer = 0.0
    total_exact_match = 0
    
    # ------------------ 新增：样本级统计列表 ------------------
    per_sample_stats = []
    
    for sample_idx, (gt_raw, pred_raw) in enumerate(zip(ground_truths_raw, predictions_raw)):
        
        # 🌟 样本级错误标志初始化
        classification_error = False # 只要有一个匹配实例的分类错误，就算该样本有错
        recognition_error = False    # 只要有一个匹配实例的 CER > 0，就算该样本有错
        
        # 假设图片ID（若无明确字段，使用索引）
        # 请根据您的实际数据结构修改 'img_id' 的获取方式
        img_id = gt_raw.get("images")[0]
        
        # 1. 解析 Loss
        sample_loss = pred_raw.get("loss", 0.0) 
        total_cross_entropy_loss += sample_loss

        # 2. 解析 Content
        try:
            gt_content_str = gt_raw["messages"][-1]["content"]
            pred_content_str = pred_raw["messages"][-1]["content"]
        except (KeyError, IndexError):
            # 解析失败，视为全部出错，并跳过评估
            per_sample_stats.append({
                "img_id": img_id,
                "分类_出错": True,
                "检测_出错": True,
                "识别_出错": True,
            })
            print(f"警告: 样本 {img_id} 解析失败, 跳过该样本评估。")
            continue

        gt_items = parse_assistant_content(gt_content_str)
        pred_items = parse_assistant_content(pred_content_str)

        gt_boxes = [item['box'] for item in gt_items]
        gt_labels = [class_to_idx.get(item['label_str'], -1) for item in gt_items]
        gt_contents = [item['content'] for item in gt_items]
        
        pred_boxes = [item['box'] for item in pred_items]
        pred_labels = [class_to_idx.get(item['label_str'], -1) for item in pred_items]
        pred_contents = [item['content'] for item in pred_items]

        total_gt_boxes += len(gt_boxes)
        total_pred_boxes += len(pred_boxes)
        
        # 3. 匹配和评估 (贪婪匹配)
        matched_gt = [False] * len(gt_boxes)
        sample_true_positives = 0 # 样本级的TP计数

        for i in range(len(pred_boxes)):
            pred_box = pred_boxes[i]
            pred_label = pred_labels[i]
            pred_content = pred_contents[i]
            
            best_iou = 0.0
            best_gt_idx = -1
            
            for j in range(len(gt_boxes)):
                if not matched_gt[j]:
                    iou = calculate_iou(pred_box, gt_boxes[j])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = j
            
            if best_iou >= iou_threshold and best_gt_idx != -1:
                # 全局指标更新
                matched_gt[best_gt_idx] = True
                true_positives += 1
                total_matched_instances += 1
                sample_true_positives += 1
                
                gt_label = gt_labels[best_gt_idx]
                gt_content = gt_contents[best_gt_idx]

                # 🌟 样本级错误判断 - 分类
                if pred_label != gt_label:
                    classification_error = True
                
                if pred_label == gt_label:
                    correct_classification += 1
                
                # 🌟 样本级错误判断 - 识别
                cer = calculate_cer(gt_content, pred_content)
                if cer > 0.0:
                    recognition_error = True
                    
                total_cer += cer
                if cer == 0.0:
                    total_exact_match += 1
        
        # 🌟 样本级错误判断 - 检测
        # 如果 TP < GT (存在 FN), 或 P != TP (存在 FP), 则视为检测错误
        if sample_true_positives < len(gt_boxes) or sample_true_positives < len(pred_boxes):
             detection_error = True
        else:
             detection_error = False

        # 记录该样本的错误状态
        per_sample_stats.append({
            "img_id": img_id,
            "分类_出错": classification_error,
            "检测_出错": detection_error,
            "识别_出错": recognition_error,
        })


    # 4. 结果汇总 (全局指标)
    mean_cross_entropy_loss = total_cross_entropy_loss / total_samples if total_samples > 0 else 0.0
    
    precision = true_positives / total_pred_boxes if total_pred_boxes > 0 else 0.0
    recall = true_positives / total_gt_boxes if total_gt_boxes > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    classification_accuracy = correct_classification / total_matched_instances if total_matched_instances > 0 else 0.0
    
    mean_cer = total_cer / total_matched_instances if total_matched_instances > 0 else 1.0
    exact_match_rate = total_exact_match / total_matched_instances if total_matched_instances > 0 else 0.0
    
    # 5. 将样本统计转换为 DataFrame
    df_error_stats = pd.DataFrame(per_sample_stats)

    results = {
        "Mean_Cross_Entropy_Loss": mean_cross_entropy_loss,
        "Detection_Precision_IoU50": precision,
        "Detection_Recall_IoU50": recall,
        "Detection_F1_Score_IoU50": f1_score,
        "Classification_Accuracy_on_Matched": classification_accuracy,
        "Mean_Character_Error_Rate (CER)": mean_cer,
        "Recognition_Exact_Match_Rate": exact_match_rate,
        "Total_Samples": total_samples,
        "Total_GT_Boxes": total_gt_boxes,
        "Total_Pred_Boxes": total_pred_boxes,
        # 🌟 新增结果：每张图片的错误统计 DataFrame
        # "Per_Sample_Error_Stats_DF": df_error_stats,
    }

    return results,df_error_stats
# --- III. 数据集加载函数 ---

def load_data_from_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """从 JSON Lines 文件中加载数据。"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line))
    except FileNotFoundError:
        print(f"错误: 文件未找到: {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败于文件 {file_path}: {e}")
        return []
    return data

# --- IV. 主执行函数 (Main) ---

def eval_fun(gt_file_path: str, pred_file_path: str, iou_threshold: float = 0.6):
    """
    主执行函数，加载数据，执行评估并打印结果。
    
    Args:
        gt_file_path: 真实标签 JSONL 文件路径。
        pred_file_path: 模型预测 JSONL 文件路径。
        iou_threshold: IoU 阈值。
    """
    
    # 定义类别到索引的映射
    CLASS_TO_IDX = {'formula': 0, 'chinese': 1, 'scribbles': 2, 'qnum': 3}
    
    print(f"--- 🚀 正在加载数据集... ---")
    
    # 1. 加载数据
    ground_truths_raw = load_data_from_jsonl(gt_file_path)
    predictions_raw = load_data_from_jsonl(pred_file_path)
    
    if not ground_truths_raw or not predictions_raw:
        print("数据集加载失败或为空，终止评估。")
        return


    print(f"数据集加载完成。共 {len(ground_truths_raw)} 个样本。")
    print(f"--- 📊 正在执行多任务评估 (IoU 阈值: {iou_threshold})... ---")

    # 2. 执行评估
    evaluation_results,per_sample_stats = evaluate_ocr_multi_task(
        predictions_raw, 
        ground_truths_raw, 
        CLASS_TO_IDX,
        iou_threshold
    )
    
    # 3. 打印结果
    print("\n--- ✅ 评估结果汇总 ---")
    # df_error_stats = pd.DataFrame(per_sample_stats)
    per_sample_stats.to_csv(os.path.join(os.path.dirname(gt_file_path),"predict_per_sample.csv"))
    df_eval = pd.DataFrame([evaluation_results]).T
    df_eval.columns = ['result']
    df_eval.to_csv(os.path.join(os.path.dirname(gt_file_path),"eval_result.csv"))
    print(f'识别出错{per_sample_stats["识别_出错"].sum()}')
    print(f'检测出错{per_sample_stats["检测_出错"].sum()}')
    print(f'分类出错{per_sample_stats["分类_出错"].sum()}')
    print("---------------------------------")
    for k, v in evaluation_results.items():
        if isinstance(v, float):
            print(f"**{k}:** {v:.4f}")
        else:
            print(f"**{k}:** {v}")
    print("---------------------------------")
    
    print("\n评估完成。")


def main():
    # ⚠️ 替换为您的实际文件路径
    # 建议先创建两个小的 JSONL 文件进行测试
    parser = argparse.ArgumentParser(description='Step 7: 从数据库导出错误数据')
    
    # 本脚本需要的参数（通过 use_shared_params 过滤，只会接收这些参数）
    # parser.add_argument('--exam_id', type=str, required=True, help='考试ID')
    parser.add_argument('--exam_id', type=str, default='500', help='考试ID')
    parser.add_argument('--subject_id', type=str, default='1', help='科目ID')
    parser.add_argument('--question_num', type=str, default='1', help='题号')
    parser.add_argument('--Dataset_dir', type=str, default="['/data/hxf/data/label_studio_data/2025-12-31/500_1_1/qwen3vl_add_begin.jsonl']", help='数据集')
    
    args = parser.parse_args()
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_directory = os.path.join("/home/aixz/data/hxf/data/label_studio_data",current_date,str(args.exam_id)+"_"+str(args.subject_id)+"_"+str(args.question_num))
    output_eval_dir = os.path.join(output_directory,"eval")
    os.makedirs(output_eval_dir, exist_ok=True)

    # GT_FILE = os.path.join(output_directory,"qwen3vl_add_begin.jsonl")
    if "[" in args.Dataset_dir: 
        GT_FILE_list = ast.literal_eval(args.Dataset_dir)
    else:
        GT_FILE_list = [args.Dataset_dir]
    PRED_FILE = os.path.join(output_eval_dir,"predictions.jsonl")
    ground_truths_raw = []
    for GT_FILE in GT_FILE_list:
        ground_truths_raw =  load_data_from_jsonl(GT_FILE)
        ground_truths_raw.extend(ground_truths_raw)
    
    GT_FILE_all = os.path.join(output_eval_dir, "gt.jsonl")
    with open(GT_FILE_all, 'w', encoding='utf-8') as f:
        for result in ground_truths_raw:
            json_line = json.dumps(result, ensure_ascii=False)
            f.write(json_line + '\n')

    
    prompt = "detect and recognize"
    CONFIG_FILE_PATH = "/home/aixz/data/hxf/ai_check/src/hu_config.yaml"
    # image_dir =  #error_images[0]['image_path'].rsplit('/',1)[0]
    allowed_images = [x['images'][0] for x in ground_truths_raw]
    # allowed_images = ['26110000130003_00_1_3.PNG', '26110030120002_00_1_3.PNG', '26110080150005_00_1_3.PNG']
    processor = QWenInference_dect_rec_api(api_url="http://192.168.1.210:9025/v1/chat/completions", prompt=prompt, max_concurrent_tasks=4,)

    try:
        results = asyncio.run(processor.run_full(output_eval_dir, allowed_images=allowed_images, method="folder", config_path=CONFIG_FILE_PATH))
    except RuntimeError as e:
        logging.error(f"运行异步任务时出错: {e}")
    
    with open(PRED_FILE, 'w', encoding='utf-8') as f:
        # 样本 1 (PRED)
        df = pd.read_csv(os.path.join(output_eval_dir,"qwen_ocr.txt"), sep="\t" )
        for index, row in df.iterrows():
            json.dump({"messages": [{"role": "assistant", "content": row["result"]}],'image':row["img_name"]}, f, ensure_ascii=False)
            f.write('\n')

            # f.write(json.dumps(result, ensure_ascii=False) + '\n')

    eval_fun(GT_FILE_all, PRED_FILE)

if __name__ == '__main__':
    sys.exit(main())
# --- ✅ 评估结果汇总 ---
# 识别出错249
# 检测出错301
# 分类出错10
# ---------------------------------
# **Mean_Cross_Entropy_Loss:** 0.0000
# **Detection_Precision_IoU50:** 0.4496
# **Detection_Recall_IoU50:** 0.4456
# **Detection_F1_Score_IoU50:** 0.4476
# **Classification_Accuracy_on_Matched:** 0.9782
# **Mean_Character_Error_Rate (CER):** 0.4744
# **Recognition_Exact_Match_Rate:** 0.0000
# **Total_Samples:** 504
# **Total_GT_Boxes:** 1030
# **Total_Pred_Boxes:** 1021
# ---------------------------------