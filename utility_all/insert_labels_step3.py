# conda activate unimernet
from label_studio_sdk import Client
from PIL import Image
import os
import os
import base64 # <-- 新增导入 base64
from datetime import datetime
import requests
from label_studio_sdk import Client
from PIL import Image
import os
import os
import base64 # <-- 新增导入 base64

import requests
import pymysql
import pymysql.cursors
from typing import List, Dict, Any
import pandas as pd
import requests
import json
import argparse
import sys
# if run_mode == "local":
#     
# storage_title = f"recoginse_20251120"
# LS_URL = 'http://localhost:5002'
# project_id = 18

def run(storage_title,LS_URL,final_tasks_payload):
    # 辅助函数：将本地文件转换为 Base64 Data URI 格式
    def local_file_to_base64(file_path):
        # 假设文件类型是 PNG，如果不是，需要根据实际情况修改 'image/png'
        # 也可以使用 PIL 动态获取类型，但这里简化为 PNG
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"



    # 获取 access token
    def get_access_token(LS_URL, personal_access_token):
        refresh_url = f"{LS_URL}/api/token/refresh"
        response = requests.post(refresh_url, json={"refresh": personal_access_token})
        response.raise_for_status()
        access_token = response.json().get("access")
        return access_token

    def get_headers(LS_URL, personal_access_token):
        access_token = get_access_token(LS_URL=LS_URL, personal_access_token=personal_access_token)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        return headers





    # nohup label-studio start --port 5002 &
    # --- 配置参数 ---
    # 请替换为你的实际地址
    PAT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6ODA3MDIwMjE1MSwiaWF0IjoxNzYzMDAyMTUxLCJqdGkiOiI1OTllNWRjNTY3OTc0OWI5OGE4ZmFlMDlhZWVkNzczYiIsInVzZXJfaWQiOiIxIn0.phquUwHP-hqdctcocKBxbwYyInpwdhUbjmDisDluYB0'             # 请替换为你的 PAT
    #   <Image name="image" value="$ocr"/>
    label_config_ocr ="""
    <View>
    <Image name="image" value="$file"/>

    <Labels name="label" toName="image" choice="single">  <Label value="formula" background="#FF3333"/>
        <Label value="chinese" background="#33FF33"/>
        <Label value="scribbles" background="#3333FF"/>
        <Label value="qnum" background="#FFFF33"/>
    </Labels>
    
    <Rectangle name="bbox" toName="image" strokeWidth="3"/>
    <Polygon name="poly" toName="image" strokeWidth="3"/>
    
    <TextArea name="transcription" toName="image"
                editable="true"
                perRegion="true"
                rows="5"
                maxSubmissions="1"
                placeholder="Recognized Text"
                displayMode="region-list"/>
                
    </View>
    """

    # 清理 XML 配置，确保它可以在 JSON 中安全传输
    def clean_xml_config(xml_string):
        # 移除所有换行符和制表符
        xml_string = xml_string.replace('\n', ' ').replace('\t', ' ')
        # 压缩多余空格
        xml_string = ' '.join(xml_string.split())
        return xml_string
    # --- 准备请求 ---

    API_ENDPOINT = f"{LS_URL}/api/projects"


    headers = get_headers(LS_URL=LS_URL, personal_access_token=PAT)
    # payload = {
    #     "title": "recoginse_1119",
    #     "description": "通过 requests 库创建的项目。",
    #     "label_config": clean_xml_config(label_config_ocr),
    #     "sampling_strategy": "sequential"
    # }
    # --- 1. 构造 Payload ---

    payload = {
        "title": storage_title,
        "bucket": "local_source_files",
        "use_blob_urls": False,
        "can_delete_objects": True,
        "recursive_scan": True,
        "presign": False, 
        "label_config": clean_xml_config(label_config_ocr),
        "sampling_strategy": "sequential",
    }
    # --- 发送请求 ---
    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=payload)
        if response.status_code == 201:
            print("✅ 项目创建成功！")
            project_data = response.json()
            project_id = project_data['id']  # <-- Project ID 在这里被成功提取
            print(f"新项目 ID: {project_data['id']}, 标题: {project_data['title']}")
        else:
            # 打印错误信息
            print(f"❌ 项目创建失败。状态码: {response.status_code}")
            print(f"错误详情: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"连接错误: {e}")



    # 【重要】任务导入 API 端点
    API_ENDPOINT = f"{LS_URL}/api/projects/{project_id}/import" 
    headers = get_headers(LS_URL=LS_URL, personal_access_token=PAT)
    payload = final_tasks_payload

    print(f"📡 正在发送请求到: {API_ENDPOINT}")
    try:
        # 使用 json=payload 自动将 Python 列表/字典序列化为 JSON
        response = requests.post(API_ENDPOINT, headers=headers, json=payload)
        
        if response.status_code == 201 or response.status_code == 200:
            print(f"✅ 任务导入成功！共导入 {len(payload)} 条任务。")
            # API 会返回一个包含任务信息的列表
            # print(response.json())
        elif response.status_code == 404:
            print(f"❌ 导入失败。请检查项目 ID: {project_id} 是否存在。")
        else:
            print(f"❌ 导入失败。状态码: {response.status_code}")
            print(f"错误详情: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"连接错误或请求异常: {e}")


def main():
    """主函数"""

    
    parser = argparse.ArgumentParser(description='Step 3: Label Studio 库生成')
    
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
    storage_title = f"recoginse_{str(args.exam_id)}_{args.subject_id}_{args.question_num}"
    print("=" * 60)
    print("Step 3: Label Studio 库生成")
    print("=" * 60)
    print(f"存储标题: {storage_title}")
    # print(f"Label Studio URL: {args.LS_URL}")
    # if args.output_directory:
    #     print(f"输出目录: {args.output_directory}")
    print("")
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_directory = os.path.join("/home/aixz/data/hxf/data/label_studio_data",current_date,str(args.exam_id)+"_"+str(args.subject_id)+"_"+str(args.question_num))

    with open(os.path.join(output_directory,"final_tasks_payload.json"), "r") as file:
        final_tasks_payload = json.load(file)
    # 调用主要逻辑
    run(storage_title,args.LS_URL,final_tasks_payload)
    
    print("")
    print("=" * 60)
    print("Step 3 执行完成！")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
