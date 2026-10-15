import sys
import os
import logging
import json
import requests
import time
import pickle
import pandas as pd
import threading
import concurrent.futures
import re
import asyncio
from typing import Dict, Any, List, Optional, Literal, Tuple
from pydantic import BaseModel
from minio import Minio
import shutil
from pathlib import Path
from minio import Minio
import json
import base64
from PIL import Image
import io
import os
import uuid
import pickle
from pathlib import Path

from datetime import datetime
import json
import os
from PIL import Image
import argparse
import uuid # 必须导入 uuid 来生成唯一的 region ID
os.chdir("/home/aixz/data/hxf/ai_check/src")
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(project_root,"src"))
from models.ocr_model.utils.hu_rec_qwen3VL_api import QWenInference_dect_rec_api
def transform_to_label_studio_format(input_task: Tuple[str, list, float],add_box:List[int] = [0,0,0,0]) -> list:
    """
    将自定义单个任务列表 [图片路径, 标注JSON字符串, 置信度分数] 转换为 
    Label Studio 任务导入格式（支持多标注框和本地文件引用）。
    
    Args:
        input_task: 包含单个任务信息的列表。
    
    Returns:
        list: 包含单个任务字典的 Label Studio 任务导入列表。
    """
    
    image_path = input_task[0]
    anno_json_str = input_task[1]
    score = input_task[2]
    
    # 1. 处理图片路径和尺寸
    if not os.path.exists(image_path):
        print(f"跳过任务，文件不存在: {image_path}")
        return []
        
    # **【修改点 1：使用本地文件路径引用】**
    image_data_uri = local_file_to_base64(image_path)

    try:
        img = Image.open(image_path)
        original_width, original_height = img.size
    except Exception as e:
        print(f"无法读取图片尺寸: {e}")
        return []

    # 2. 解析标注JSON字符串
    # try:
    #     custom_annotations = anno_json_str
    # except json.JSONDecodeError as e:
    #     print(f"解析标注JSON失败: {e}")
    #     return []
    custom_annotations = anno_json_str
    # 3. 转换标注结果 (result) 结构
    
    ls_results = []
    
    # **【修改点 2：循环处理所有标注对象】**
    for anno in custom_annotations:
        
        # 为每一个标注对象生成一个唯一的 ID，用于绑定 BBox/Label/Textarea
        REGION_ID = str(uuid.uuid4()) 
        x_min, y_min, x_max, y_max = anno['bbox'] 
        x_min += add_box[0]
        y_min += add_box[1]
        x_max += add_box[2]
        y_max += add_box[3]
        x_min = max(0, min(x_min, original_width))
        y_min = max(0, min(y_min, original_height))
        x_max = max(0, min(x_max, original_width))
        y_max = max(0, min(y_max, original_height))
        if x_max < x_min:
            x_max = x_min
        if y_max < y_min:
            y_max = y_min   
        # 将像素坐标转换为百分比坐标 (Label Studio 需要)
        width_percent = (x_max - x_min) / original_width * 100
        height_percent = (y_max - y_min) / original_height * 100
        x_percent = x_min / original_width * 100
        y_percent = y_min / original_height * 100
        
        # A. BBox (Rectangle)
        ls_results.append({
            "original_width": original_width, 
            "original_height": original_height,
            "value": {
                "x": x_percent, "y": y_percent, "width": width_percent, "height": height_percent, "rotation": 0
            },
            "id": REGION_ID,
            "from_name": "bbox", "to_name": "image", "type": "rectangle"
        })
        
        # B. Transcription (TextArea) - 使用 'latex' 字段作为文本
        # 注意：如果 'latex' 字段不存在，这里会出错。确保输入数据结构一致。
        ls_results.append({
            "value": {"text": [anno.get('text', "")]}, # 使用 .get 避免 key error
            "id": REGION_ID,
            "from_name": "transcription", "to_name": "image", "type": "textarea"
        })
        
        # C. Labels (Labels) - 使用 'category' 字段作为标签
        ls_results.append({
            "value": {"labels": [anno['category']]},
            "id": REGION_ID,
            "from_name": "label", "to_name": "image", "type": "labels"
        })
        
    # 4. 组装最终结构
    label_studio_task = {
        "data": {
            # **【修改点 1：使用本地文件引用格式】**
            "file": image_data_uri,
            "image_path": image_path,
        },
        "predictions": [
            {
                "result": ls_results,
            }
        ]
    }
    
    return [label_studio_task]

def local_file_to_base64(file_path):
    """将本地图片文件转换为 Base64 Data URI 格式"""
    import mimetypes
    # 尝试猜测 MIME 类型
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'
        
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        return f"data:{mime_type};base64,{encoded_string}"
    except FileNotFoundError:
        print(f"❌ 错误: 图片文件未找到于 {file_path}")
        return None

# if run_mode == "local":
#     output_directory = '/home/aixz/data/hxf/data/label_studio_data/result/image_20251120'

def run(output_directory,api_url,localimage_dir):
    os.makedirs(output_directory, exist_ok=True)

    prompt = "detect and recognize"
    # allowed_images = os.listdir(image_folder)#[:100]
    CONFIG_FILE_PATH = "/home/aixz/data/hxf/ai_check/src/hu_config.yaml"

    if localimage_dir=="$" or len(localimage_dir)<5:
        with open(os.path.join(output_directory, f'error_images.pkl'), 'rb') as f:
            error_images = pickle.load(f)
        image_dir = error_images[0]['image_path'].rsplit('exam/',1)[-1].rsplit("/",1)[0]
        allowed_images = [x['image_path'].split('/')[-1] for x in error_images]
        import random
        allowed_images = random.sample(allowed_images, min(100,len(allowed_images)))
        method = "minio"
    else:
        image_dir = localimage_dir
        allowed_images = os.listdir(image_dir)
        method = "folder"

    if 1==1:
        # api_url = "http://192.168.1.210:9009/v1/chat/completions"
        processor = QWenInference_dect_rec_api(api_url=api_url, prompt=prompt, max_concurrent_tasks=4,)

        try:
            results = asyncio.run(processor.run(image_dir,output_directory, allowed_images=allowed_images, method=method, config_path=CONFIG_FILE_PATH))
        
            # save_result(output_directory, results)
        except RuntimeError as e:
            logging.error(f"运行异步任务时出错: {e}")

        with open(os.path.join(output_directory, "results.pkl"), "wb") as f:
            pickle.dump(results, f)
    # ('/home/aixz/data/hxf/data/label_studio_data/result/image_20251113/resized_image/33003000720045_00_1_4.PNG', [{'bbox': [152, 214, 208, 416], 'category': 'formula', 'text': '$\\pi$'}, {'bbox': [19, 300, 56, 416], 'category': 'qnum', 'text': '$20.$'}], 0.85)
    with open(os.path.join(output_directory, "results.pkl"), "rb") as f:
        results = pickle.load(f)

    all_input_data = results
    final_tasks_payload = []
    for task_data in all_input_data:
        try:
            annotations = task_data[1]
            has_pi = False
            for item in annotations:
                # if 'text' in item and '\\pi' in item['text']:
                    # continue
                # if 'text' in item and item['category'] == 'formula':
                #     item['text'] = f"$1 5 或 - 5$"
                pass
                    
            if has_pi:
                continue
            converted_task = transform_to_label_studio_format(task_data,add_box=[0,0,0,0])
        except Exception as e:
            print(f"转换任务 {task_data} 时出错: {e}")
            continue
        if converted_task:
            final_tasks_payload.extend(converted_task)
    with open(os.path.join(output_directory, "final_tasks_payload.json"), "w") as f:
        json.dump(final_tasks_payload, f, ensure_ascii=False, indent=4)

    print(f"成功转换 {len(final_tasks_payload)} 个任务。")

def main():
    """主函数"""

    parser = argparse.ArgumentParser(description='Step 2: 预打标')
    # parser.add_argument('--output_directory', type=str, required=True, help='输出目录')
    parser.add_argument('--exam_id', type=str, default='475', help='考试ID')
    parser.add_argument('--subject_id', type=str, default='2119', help='科目ID')
    parser.add_argument('--question_num', type=str, default='24', help='题号')
    parser.add_argument('--api_url', type=str, default='http://192.168.1.210:9009/v1/chat/completions', help='推理接口')
    parser.add_argument('--localimage_dir', type=str, default='', help='图片的目录')
    # parser.add_argument('--LS_URL', type=str, default='http://localhost:5002', help='Label Studio URL')
    # parser.add_argument('--api_url', type=str, help='API地址（本脚本不使用）')
    # parser.add_argument('--storage_title', type=str, help='存储标题（本脚本不使用）')
    # parser.add_argument('--LS_URL', type=str, help='Label Studio URL（本脚本不使用）')
    
    args = parser.parse_args()
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_directory = os.path.join("/home/aixz/data/hxf/data/label_studio_data",current_date,str(args.exam_id)+"_"+str(args.subject_id)+"_"+str(args.question_num))
    run(output_directory,args.api_url,args.localimage_dir)
    print("=" * 60)
    print("Step 2:")
    print("=" * 60)
    print(f"输出目录: {output_directory}")
    print("")

if __name__ == '__main__':
    sys.exit(main())