#!/bin/bash
# 快速启动脚本

cd "$(dirname "$0")"

echo "================================"
echo "启动 Python 程序执行界面"
echo "================================"
echo ""

# 检查 Flask
if ! python -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask 未安装，正在安装..."
    pip install Flask
    echo ""
fi

# 检查端口
PORT=5001
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用"
    echo "正在尝试使用端口 5002..."
    PORT=5002
fi

echo "✓ 启动服务..."
echo "✓ 访问地址: http://localhost:$PORT"
echo ""
echo "按 Ctrl+C 停止服务"
echo "================================"
echo ""

python app.py
