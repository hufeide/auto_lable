#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1: 从数据库导出错误数据
从 MySQL 数据库查询 AI 阅卷结果与人工校对不一致的图片信息
"""

import time 
from datetime import datetime
import argparse
import sys
import os
import pickle
import pymysql
import pymysql.cursors
from typing import List, Dict, Any
import pandas as pd
def get_error_correction_details(
    examId: int, 
    subjectId: int, 
    model_question_num: str = '20',
    sql_query: str = None
) -> List[Dict[str, Any]]:
    """
    连接数据库并执行特定的SQL查询，以获取AI阅卷结果与人工校对结果不一致的图片路径和名称。

    Args:
        examId: 考试ID，用于构建数据库名。
        subjectId: 科目ID，用于构建数据库名。
        model_question_num: 模型问题编号，默认为 '20'。
        
    Returns:
        包含查询结果（每项为字典）的列表，如果查询失败返回空列表。
    """
    
    # 构建数据库名 auto_check_473_2106
    db_name = f'auto_check_{examId}_{subjectId}'
    connection = None
    
    # 🌟 目标查询
    # sql_query = f"""
    # SELECT 
    #     image_path, 
    #     image_name 
    # FROM 
    #     auto_model_correction_result_detail 
    # WHERE 
    #     model_question_num = '{model_question_num}' 
    #     AND ai_all_correction_result < 99 
    #     AND ABS(ai_all_correction_result - qt_correction_result) > 0;
    # """

    try:
        # 建立数据库连接
        connection = pymysql.connect(
            host='192.168.1.210',
            user='root',
            password='123456',
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            # 执行 SQL 查询
            # 打印 SQL 语句方便调试
            print(f"Executing SQL on database '{db_name}':\n{sql_query}") 
            
            cursor.execute(sql_query)
            
            # 获取所有查询结果
            results = cursor.fetchall()
            
            return results

    except pymysql.Error as e:
        print(f"数据库错误 (DB: {db_name}): {e}")
        return [] # 失败时返回空列表
        
    except Exception as e:
        print(f"发生未知错误: {e}")
        return []
        
    finally:
        if connection:
            connection.close()
def run(sql_query,output_directory, exam_id, subject_id, question_num):

    
    print("正在查询数据库...")
    # 执行查询
    error_images = get_error_correction_details(
        int(exam_id), 
        int(subject_id), 
        question_num, 
        sql_query
    )
    
    if error_images:
        print(f"✓ 找到 {len(error_images)} 条 AI 结果与人工校对不一致的记录")
        
        # 保存结果到 pickle 文件
        output_file = os.path.join(output_directory, 'error_images.pkl')
        with open(output_file, 'wb') as f:
            pickle.dump(error_images, f)
        print(f"✓ 数据已保存到: {output_file}")
        
        # 显示前几条记录
        df_errors = pd.DataFrame(error_images)
        print("\n前 5 条记录:")
        print(df_errors.head())
        
        # 提取图片名称列表
        image_names = [x['image_name'] for x in error_images]
        print(f"\n✓ 共 {len(image_names)} 张图片")
        
    else:
        print("✗ 未找到符合条件的记录或数据库连接失败")
        return 1

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Step 1: 从数据库导出错误数据')
    
    # 本脚本需要的参数（通过 use_shared_params 过滤，只会接收这些参数）
    parser.add_argument('--exam_id', type=str, required=True, help='考试ID')
    parser.add_argument('--subject_id', type=str, required=True, help='科目ID')
    parser.add_argument('--question_num', type=str, required=True, help='题号')
    
    args = parser.parse_args()

    print("=" * 60)
    print("Step 1: 从数据库导出错误数据")
    print("=" * 60)
    print(f"考试ID: {args.exam_id}")
    print(f"科目ID: {args.subject_id}")
    print(f"题号: {args.question_num}")

    
    # 1. 获取当前日期，并格式化为字符串 (例如: "2023-10-27")
    # %Y=年, %m=月, %d=日
    current_date = datetime.now().strftime("%Y-%m-%d")
    timestamp = str(int(time.time()))
    output_directory = os.path.join("/home/aixz/data/hxf/data/label_studio_data",current_date,str(args.exam_id)+"_"+str(args.subject_id)+"_"+str(args.question_num))
    # 确保输出目录存在
    os.makedirs(output_directory, exist_ok=True)
    sql_query = f"""
    SELECT 
        CONCAT('http://192.168.1.210:9000', image_path) as image_path,
        image_name 
    FROM 
        auto_check_{args.exam_id}_{args.subject_id}.auto_model_correction_result_detail 
    WHERE 
        model_question_num = {args.question_num} 
        AND flag = 1 
        AND ai_all_correction_result < 99 
        AND ABS(ai_all_correction_result - qt_correction_result) > 0
    limit 10
    """
    run(sql_query,output_directory, int(args.exam_id), int(args.subject_id), args.question_num)
    
    # 构建 SQL 查询

    
    print("")
    print("=" * 60)
    print("Step 1 执行完成！")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())