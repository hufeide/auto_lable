#!/bin/bash
# Bash 脚本示例
# 可以通过位置参数或环境变量获取参数

echo "================================"
echo "Bash 脚本开始执行"
echo "================================"

# 方式1: 通过位置参数获取
if [ $# -gt 0 ]; then
    echo "位置参数:"
    for i in "$@"; do
        echo "  - $i"
    done
fi

# 方式2: 通过环境变量获取（推荐）
if [ ! -z "$MESSAGE" ]; then
    echo "MESSAGE 参数: $MESSAGE"
fi

if [ ! -z "$COUNT" ]; then
    echo "COUNT 参数: $COUNT"
    echo ""
    echo "执行循环 $COUNT 次:"
    for i in $(seq 1 $COUNT); do
        echo "  第 $i 次执行"
        sleep 0.5
    done
fi

# 执行一些系统命令
echo ""
echo "系统信息:"
echo "  当前用户: $(whoami)"
echo "  当前目录: $(pwd)"
echo "  当前时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 模拟一些处理
echo ""
echo "正在处理数据..."
sleep 1
echo "处理完成！"

echo "================================"
echo "Bash 脚本执行完成"
echo "================================"

exit 0
