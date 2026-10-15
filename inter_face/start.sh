#!/bin/bash
# 启动 Flask 应用

echo "================================"
echo "启动 Python 程序执行界面"
echo "================================"

# 检查 Flask 是否安装
if ! python -c "import flask" 2>/dev/null; then
    echo "Flask 未安装，正在安装..."
    pip install Flask
fi

# 启动应用
echo ""
echo "启动服务..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务"
echo ""

python app.py
