import json
import os
import cv2
import numpy as np
import math
import random
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

# --- 类型定义 ---
OriginalData = Dict[str, Any]
TargetData = Dict[str, Any]

# --- 全局配置 ---
SYSTEM_PROMPT = (
    "You are a multimodal OCR detector and recognizer. "
    "Detect all elements: 'formula','chinese','scribbles','qnum'. each with a bounding box e.g., (x1,y1),(x2,y2)"
    "also include its content, e.g., formula:'$2x + 3 = 7$'. "
)

# --- 核心逻辑函数 ---

def parse_txt_to_original_format(txt_filepath: str, image_dir: str) -> Optional[Dict[str, Any]]:
    """
    解析标签文件。兼容制表符和空格，增加了路径查找的灵活性。
    """
    # 兼容文件名处理逻辑
    base_name = os.path.basename(txt_filepath)
    # 尝试多种可能的图片对应关系
    possible_img_names = [
        base_name.replace('.txt', '.PNG'),
        base_name.replace('.txt', '.png'),
        base_name.replace('.txt', '.jpg')
    ]
    
    image_path = None
    for name in possible_img_names:
        temp_path = os.path.join(image_dir, name)
        if os.path.exists(temp_path):
            image_path = temp_path
            break
    
    if not image_path:
        return None

    objects = []
    try:
        with open(txt_filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                # 兼容 \t 分隔或多空格分隔
                parts = line.split('\t') if '\t' in line else line.split()
                
                if len(parts) >= 3:
                    # 预期格式: box, transcription, category
                    box_str, transcription, category = parts[0], parts[1], parts[2]
                    
                    # 尝试解析坐标 xmin,ymin,xmax,ymax
                    try:
                        coords = [float(c) for c in box_str.replace(' ', '').split(',')]
                        if len(coords) == 4:
                            xmin, ymin, xmax, ymax = coords
                            bbox = [int(xmin), int(ymin), int(xmax), int(ymax)]
                            
                            objects.append({
                                "bbox": bbox,
                                "category": category,
                                "transcription": transcription
                            })
                    except ValueError:
                        continue
    except Exception as e:
        print(f"解析文件出错 {txt_filepath}: {e}")
        return None

    return {"image_path": image_path, "objects": objects} if objects else None

def get_new_size_and_factors(orig_w: int, orig_h: int, target_size_multiple: int = 28, target_short_side: int = None):
    multiple = max(1, target_size_multiple)
    if target_short_side:
        scale = target_short_side / min(orig_h, orig_w)
        new_w = math.ceil((orig_w * scale) / multiple) * multiple
        new_h = math.ceil((orig_h * scale) / multiple) * multiple
    else:
        new_w = math.ceil(orig_w / multiple) * multiple
        new_h = math.ceil(orig_h / multiple) * multiple
    
    new_w, new_h = max(new_w, multiple), max(new_h, multiple)
    return new_w, new_h, new_w / orig_w, new_h / orig_h

def transform_data_for_llm(
    original_data: OriginalData, 
    target_size_multiple: int = 28, 
    system_prompt: str = SYSTEM_PROMPT,
    output_png_path: str = None,
    target_short_side: int = None
) -> Optional[TargetData]:
    img_path = original_data["image_path"]
    img = cv2.imread(img_path)
    if img is None: return None
        
    orig_h, orig_w = img.shape[:2]
    new_w, new_h, scale_x, scale_y = get_new_size_and_factors(orig_w, orig_h, target_size_multiple, target_short_side)
    
    # 调试时可开启 resize
    # resized_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    message_content_parts = []
    category_map = {
        "shuxue": "formula", "tihao": "qnum", 
        "yuwen": "chinese", "tugai": "scribbles"
    }
    
    for obj in original_data["objects"]:
        cat = obj["category"]
        category = category_map.get(cat, cat)
        transcription = obj.get("transcription", "")
        
        if transcription == "UNKNOWN": return None
        if category == "scribbles": transcription = ""

        # 归一化坐标计算 (基于新尺寸)
        x1, y1, x2, y2 = obj["bbox"]
        norm_x1 = int(np.clip(round((x1 * scale_x) / new_w * 999), 0, 999))
        norm_y1 = int(np.clip(round((y1 * scale_y) / new_h * 999), 0, 999))
        norm_x2 = int(np.clip(round((x2 * scale_x) / new_w * 999), 0, 999))
        norm_y2 = int(np.clip(round((y2 * scale_y) / new_h * 999), 0, 999))
        
        box_str = f"({norm_x1},{norm_y1}),({norm_x2},{norm_y2})"
        description = f"{category}:'${transcription}$'" if transcription else category
        
        message_content_parts.append(
            f"<|box_start|>{box_str}<|box_end|><|object_ref_start|>{description}<|object_ref_end|>"
        )

    # 模拟保存路径，保持 logic 一致
    img_save_name = os.path.basename(img_path)
    final_img_path = os.path.join(output_png_path, img_save_name) if output_png_path else img_path

    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "<image>detect and recognize"}, 
            {"role": "assistant", "content": "".join(message_content_parts)}
        ],
        "images": [final_img_path]
    }

def process_single_file(txt_filepath: str, image_dir: str, output_png_root: str):
    original_data = parse_txt_to_original_format(txt_filepath, image_dir)
    if not original_data: return None
    return transform_data_for_llm(original_data, output_png_path=output_png_root)

# --- 执行入口 ---

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exam_id', type=str, default='500')
    parser.add_argument('--subject_id', type=str, default='1')
    parser.add_argument('--question_num', type=str, default='1')
    parser.add_argument('--debug', default=False, help='开启单文件调试模式')
    # parser.add_argument('--debug', default='False', action='store_true', help='开启单文件调试模式')
    args = parser.parse_args()

    current_date = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join("/home/aixz/data/hxf/data/label_studio_data", 
                              current_date, 
                              f"{args.exam_id}_{args.subject_id}_{args.question_num}")

    LABEL_ROOT = os.path.join(output_dir, "label")
    IMAGE_ROOT = os.path.join(output_dir, "resized_image")
    OUTPUT_JSONL = os.path.join(output_dir, "qwen3vl_add_begin.jsonl")
    OUTPUT_PNG_DIR = IMAGE_ROOT#os.path.join(output_dir, "finall_png")

    os.makedirs(os.path.dirname(OUTPUT_JSONL), exist_ok=True)
    os.makedirs(OUTPUT_PNG_DIR, exist_ok=True)

    # 调试模式：只处理第一个文件并打印
    if args.debug:
        print("--- 调试模式开启 ---")
        test_files = [f for f in os.listdir(LABEL_ROOT) if f.endswith('.txt')]
        if test_files:
            res = process_single_file(os.path.join(LABEL_ROOT, test_files[0]), IMAGE_ROOT, OUTPUT_PNG_DIR)
            print(json.dumps(res, indent=4, ensure_ascii=False))
        else:
            print("未找到测试标签文件")
        return

    # 批量处理逻辑
    all_txt = [os.path.join(LABEL_ROOT, f) for f in os.listdir(LABEL_ROOT) if f.endswith('.txt')]
    if not all_txt:
        print(f"路径为空: {LABEL_ROOT}")
        return

    MAX_WORKERS = max(1, os.cpu_count() // 2)
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as outfile:
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_single_file, tp, IMAGE_ROOT, OUTPUT_PNG_DIR) for tp in all_txt]
            for future in tqdm(as_completed(futures), total=len(all_txt), desc="转换中"):
                res = future.result()
                if res:
                    json.dump(res, outfile, ensure_ascii=False)
                    outfile.write('\n')
    print(f"训练集完成")

if __name__ == '__main__':
    main()