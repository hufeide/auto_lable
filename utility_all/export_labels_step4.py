
# conda activate unimernet
from label_studio_sdk import Client
from PIL import Image
import os
import os
import base64 # <-- 新增导入 base64
import sys
import requests
from label_studio_sdk import Client
from PIL import Image
import os
import os
import base64 # <-- 新增导入 base64
from datetime import datetime
import requests
import pymysql
import pymysql.cursors
from typing import List, Dict, Any
import pandas as pd
import requests
import json
import json
import os
import re
# nohup label-studio start --port 5002 &
# --- 配置参数 ---
# if run_mode == "local":
#     storage_title = "recoginse_20251120"
#     LS_URL = 'http://localhost:5002' # 请替换为你的实际地址
#     output_label_dir = '/home/aixz/data/hxf/data/label_studio_data/result/image_20251120/label' 
PAT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6ODA3MDIwMjE1MSwiaWF0IjoxNzYzMDAyMTUxLCJqdGkiOiI1OTllNWRjNTY3OTc0OWI5OGE4ZmFlMDlhZWVkNzczYiIsInVzZXJfaWQiOiIxIn0.phquUwHP-hqdctcocKBxbwYyInpwdhUbjmDisDluYB0'             # 请替换为你的 PAT

def run(storage_title,LS_URL,output_directory):
    def get_access_token(ls_url, personal_access_token):
        refresh_url = f"{ls_url}/api/token/refresh"
        response = requests.post(refresh_url, json={"refresh": personal_access_token})
        response.raise_for_status()
        access_token = response.json().get("access")
        return access_token

    def get_headers(ls_url, personal_access_token):
        access_token = get_access_token(ls_url=ls_url, personal_access_token=personal_access_token)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        return headers


    def get_project_id_by_title(project_title: str, ls_url: str, pat: str):
        """
        根据项目标题 (title) 从 Label Studio 获取对应的 project_id。
        
        Args:
            project_title: 要查找的项目的标题。
            ls_url: Label Studio 的基础 URL。
            pat: 个人访问令牌 (Personal Access Token)。
            
        Returns:
            匹配的 project_id (int) 或 None (如果未找到)。
        """
        
        API_PROJECTS_ENDPOINT = f"{ls_url}/api/projects"
        
        # 假设 get_headers 函数接受 ls_url 和 pat
        # 如果您的 get_headers 只接受 token，请自行调整
        headers = get_headers(ls_url=ls_url, personal_access_token=pat)
        
        print(f"🔍 正在尝试获取项目列表以查找标题: '{project_title}'...")

        try:
            # 使用 GET 请求获取项目列表
            # 注意：API 可能会分页，这里只处理第一页数据
            response = requests.get(API_PROJECTS_ENDPOINT, headers=headers)
            response.raise_for_status() # 检查错误
            
            projects_data = response.json()
            
            # Label Studio /api/projects 接口返回的是一个列表，或者是一个包含 'results' 键的字典（如果启用了分页）
            # 我们假设它直接返回项目列表或在 'results' 键下
            
            # 优先从 'results' 键获取列表，如果不存在，则假设响应本身就是列表
            project_list = projects_data.get('results', projects_data)

            if not isinstance(project_list, list):
                print("❌ API 响应格式不正确，无法解析项目列表。")
                return None

            for project in project_list:
                if project.get('title') == project_title:
                    project_id = project.get('id')
                    print(f"✅ 找到项目！标题: '{project_title}', ID: {project_id}")
                    return project_id

            print(f"⚠️ 未找到标题为 '{project_title}' 的项目。")
            return None

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP 错误 (状态码 {response.status_code}): 无法获取项目列表。请检查 URL 或 PAT。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 连接错误或请求异常: {e}")
            return None
        except json.JSONDecodeError:
            print(f"❌ 无法解析 API 响应为 JSON 格式。")
            return None
    output_label_dir = os.path.join(output_directory, "label")
    project_title_to_find = storage_title
    project_id = get_project_id_by_title(
        project_title=project_title_to_find, 
        ls_url=LS_URL, 
        pat=PAT
    )
    # 【另一个示例：只导出状态为 'finished' 的任务】
    export_payload = {
        "filter": {
            "status": "Completed" # 或 "completed", "skipped" 等
        }
    }

    API_ENDPOINT = f"{LS_URL}/api/projects/{project_id}/export"

    headers = get_headers(ls_url=LS_URL, personal_access_token=PAT)
    OUTPUT_FILE = os.path.join(output_directory, "storage.json")
    try:
        # 使用 json=export_payload 发送 POST 请求，指定导出过滤条件
        response = requests.get(API_ENDPOINT, headers=headers, json=export_payload)
        
        # 导出 API 可能会返回 200 OK，或者 201 Created (如果它需要排队处理)
        if response.status_code == 200:
            print("✅ 导出请求成功！正在将数据写入文件。")
            
            # 导出数据通常以 JSON 格式返回，直接将响应内容写入文件
            with open(OUTPUT_FILE, 'wb') as f:
                f.write(response.content)

            print(f"🎉 导出成功！数据已保存到: {os.path.abspath(OUTPUT_FILE)}")
            
            # 验证导出的 JSON 文件是否有效 (可选)
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"文件包含 {len(data)} 个任务。")

        else:
            print(f"❌ 导出失败。状态码: {response.status_code}")
            print(f"错误详情: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"连接错误或请求异常: {e}")




    def convert_labelstudio_json_to_txt(json_data,output_label_dir:str):
        """
        将 Label Studio 的单个任务 JSON 数据转换为 YOLO 格式的 TXT 文件内容。

        输出格式：x_min,y_min,x_max,y_max\ttext\tlabel
        坐标将从百分比转换为像素值。
        """
        # 1. 提取图片路径作为文件名
        try:
            # 从 'data' 字段中提取 'image_path' 或 'file' 对应的文件名
            # 假设文件名是 '33019000220020_00_1_4.PNG'
            file_path_in_data = json_data.get('data', {}).get('image_path')
            if not file_path_in_data:
                print("警告: 无法从 'image_path' 获取文件名。使用默认名称 'output.txt'")
                base_filename = "output"
            else:
                base_filename = os.path.basename(file_path_in_data).rsplit('.', 1)[0]
            
            output_filename = f"{base_filename}.txt"

        except Exception as e:
            print(f"处理文件名时出错: {e}. 使用默认名称 'output.txt'")
            output_filename = "output.txt"
            
        # 2. 准备存储结果的字典
        # 使用唯一的 ID (ed7c09fd-6ee8...) 作为键来组合 BBOX, TEXT, LABEL
        grouped_results = {}
        
        # 假设我们只关心第一个 annotation 中的结果
        if not json_data.get('annotations'):
            print("错误: JSON 中没有 'annotations' 数据。")
            return None

        # 提取原始尺寸
        # 遍历 result 列表中的任一元素都可以获取原始尺寸
        if json_data['annotations'][0]['was_cancelled']:
            return None
        original_width = json_data['annotations'][0]['result'][0]['original_width']
        original_height = json_data['annotations'][0]['result'][0]['original_height']
        
        if not (original_width and original_height):
            print("错误: 无法获取 original_width 或 original_height。")
            return None

        # 3. 遍历 annotations 结果
        for annotation in json_data['annotations']:
            for item in annotation['result']:
                unique_id = item['id']
                item_type = item['from_name']
                value = item['value']
                
                if unique_id not in grouped_results:
                    grouped_results[unique_id] = {}

                if item_type == 'bbox':
                    # 提取归一化坐标 (x, y, width, height)
                    x = value['x']
                    y = value['y']
                    w = value['width']
                    h = value['height']

                    # 将百分比坐标转换为像素坐标 (x_min, y_min, x_max, y_max)
                    x_min = int(x * original_width / 100)
                    y_min = int(y * original_height / 100)
                    x_max = int((x + w) * original_width / 100)
                    y_max = int((y + h) * original_height / 100)
                    
                    # 按照示例格式化坐标：x_min,y_min,x_max,y_max
                    grouped_results[unique_id]['coords'] = f"{x_min},{y_min},{x_max},{y_max}"
                    
                elif item_type == 'transcription' and 'text' in value:
                    # 提取文本。去除 Label Studio 中 LaTeX 模式下常见的 $ 包裹
                    text = value['text'][0]
                    text = re.sub(r'^\$|^\\[()](.*?)\\[)]\$|\$$', r'\1', text).strip()
                    grouped_results[unique_id]['text'] = text
                    
                elif item_type == 'label' and 'labels' in value:
                    # 提取标签
                    grouped_results[unique_id]['label'] = value['labels'][0]

        # 4. 格式化输出行
        output_lines = []
        for uid, data in grouped_results.items():
            # 确保所有必需的字段都存在
            if all(k in data for k in ['coords', 'text', 'label']):
                # 格式：94,6,146,64\t\frac { 1 3 } { 6 0 }\tformula
                if data['label']=="scribbles":
                    data['text'] = "$scribbles$"
                output_line = f"{data['coords']}\t{data['text']}\t{data['label']}"
                output_lines.append(output_line)

        # 5. 将结果写入文件
        if output_lines:
            with open(os.path.join(output_label_dir,output_filename), 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            print(f"✅ 成功将数据写入文件: {output_filename}")
            print("--- 文件内容摘要 ---")
            for line in output_lines:
                print(line)
            return output_filename
        else:
            print("⚠️ 警告: 未找到完整的 BBOX/TEXT/LABEL 组合结果，未生成文件。")
            return None


    os.makedirs(output_label_dir,exist_ok=True)
    out_list = []
    for data_one in data:
        out = convert_labelstudio_json_to_txt(data_one,output_label_dir)
        out_list.append(out)

    non_none_list = [item for item in out_list if item is not None]
    len(non_none_list)




def main():
    """主函数"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Step 4: Label Studio 库生成')
    
    # 定义所有需要的参数（这些参数会从共享参数和任务参数中获取）
    # parser.add_argument('--storage_title', type=str, required=True, help='存储标题')
    # parser.add_argument('--output_directory', type=str, help='输出目录（可选）')
    parser.add_argument('--exam_id', type=str, default='475', help='考试ID')
    parser.add_argument('--subject_id', type=str, default='2119', help='科目ID')
    parser.add_argument('--question_num', type=str, default='24', help='题号')
    parser.add_argument('--LS_URL', type=str, default='http://localhost:5002', help='Label Studio URL')
    # parser.add_argument('--api_url', type=str, help='API地址（本脚本不使用）')
    # parser.add_argument('--storage_title', type=str, help='存储标题（本脚本不使用）')

    args = parser.parse_args()
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_directory = os.path.join("/home/aixz/data/hxf/data/label_studio_data",current_date,str(args.exam_id)+"_"+str(args.subject_id)+"_"+str(args.question_num))
    storage_title = f"recoginse_{args.exam_id}_{args.subject_id}_{args.question_num}"
    
    print("=" * 60)
    print("Step 3: Label Studio 库生成")
    print("=" * 60)
    print(f"存储标题: {storage_title}")
    # print(f"Label Studio URL: {args.LS_URL}")
    # if args.output_directory:
    #     print(f"输出目录: {args.output_directory}")
    print("")
    
    # 调用主要逻辑
    run(storage_title,args.LS_URL,output_directory)
    
    print("")
    print("=" * 60)
    print("Step 4 执行完成！")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
