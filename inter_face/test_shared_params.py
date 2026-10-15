#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试共享参数的脚本
演示如何接收和使用共享参数
"""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='测试共享参数')
    
    # 定义所有可能接收的参数
    # 这些参数会从共享参数和任务参数中自动获取
    parser.add_argument('--exam_id', type=str, help='考试ID')
    parser.add_argument('--subject_id', type=str, help='科目ID')
    parser.add_argument('--question_num', type=str, help='题号')
    parser.add_argument('--output_directory', type=str, help='输出目录')
    parser.add_argument('--api_url', type=str, help='API地址')
    parser.add_argument('--storage_title', type=str, help='存储标题')
    parser.add_argument('--LS_URL', type=str, help='Label Studio URL')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("测试共享参数")
    print("=" * 60)
    print("\n接收到的参数：")
    print("-" * 60)
    
    # 显示所有接收到的参数
    for key, value in vars(args).items():
        if value is not None:
            print(f"  {key:20s} = {value}")
    
    print("-" * 60)
    print("\n✓ 参数接收成功！")
    print("\n说明：")
    print("  - 这些参数来自共享参数和任务参数的合并")
    print("  - 任务参数会覆盖同名的共享参数")
    print("  - 未设置的参数值为 None")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
