#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试脚本
"""
import argparse
import time
import sys

def main():
    parser = argparse.ArgumentParser(description='简单测试脚本')
    parser.add_argument('--exam_id', type=str, default='', help='考试ID')
    parser.add_argument('--subject_id', type=str, default='', help='科目ID')
    parser.add_argument('--question_num', type=str, default='', help='题号')
    parser.add_argument('--output_directory', type=str, default='', help='输出目录')
    args = parser.parse_args()
    
    print("=" * 50)
    print("脚本开始执行")
    print("=" * 50)
    print(f"考试ID: {args.exam_id}")
    print(f"科目ID: {args.subject_id}")
    print(f"题号: {args.question_num}")
    print(f"输出目录: {args.output_directory}")
    print("")
    
    # 模拟处理过程
    for i in range(1, 4):
        print(f"处理步骤 {i}/3...")
        time.sleep(1)
    
    print("")
    print("=" * 50)
    print("脚本执行完成！")
    print("=" * 50)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
