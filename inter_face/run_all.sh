#!/bin/bash
# 快速启动脚本
LOG_DIR="/home/aixz/data/hxf/ai_check/lablestudio/log"
mkdir -p "$LOG_DIR" # 确保日志目录存在

echo "--- 进入工作目录 ---"
cd /home/aixz/data/hxf/ai_check/lablestudio/inter_face
echo "当前工作目录: $(pwd)"
echo ""

# --- Conda 环境初始化 ---
# 尝试初始化Conda。通常conda安装后会在~/.bashrc中添加初始化代码。
# source ~/.bashrc 可以在交互式会话中工作，但在非交互式脚本中可能不够。
# 更健壮的方法是直接 sourcing conda's own initialization script.
# 查找conda.sh的路径，通常在 <conda_install_path>/etc/profile.d/conda.sh
# 如果你知道确切路径，可以直接指定，否则可以尝试查找。
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    echo "警告: 未找到 conda base 环境。请确保 conda 已安装并添加到 PATH。"
    # 尝试一个常见的默认路径
    if [ -f "/home/aixz/anaconda3/etc/profile.d/conda.sh" ]; then
        source "/home/aixz/anaconda3/etc/profile.d/conda.sh"
        echo "尝试从 /home/aixz/anaconda3/etc/profile.d/conda.sh 初始化 conda."
    elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then # 另一个常见路径
        source "/opt/conda/etc/profile.d/conda.sh"
        echo "尝试从 /opt/conda/etc/profile.d/conda.sh 初始化 conda."
    else
        echo "错误: 无法自动初始化 conda。请手动检查并确保 'conda' 命令可用。"
        exit 1
    fi
else
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    echo "从 $CONDA_BASE/etc/profile.d/conda.sh 初始化 conda."
fi

# 检查 conda 命令是否现在可用
if ! command -v conda &> /dev/null; then
    echo "错误: 即使尝试初始化后，'conda' 命令仍不可用。请检查您的 Anaconda/Miniconda 安装。"
    exit 1
fi

conda activate myollama
echo ""

echo "--- 1. 启动 Yolo GPU 检测服务 (端口 2000) ---"
bash /home/aixz/data/hxf/ai_check/src/kill_bash.sh 8091
nohup label-studio start --port 8091 > ls_log.txt 2>&1 &


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

python app_all.py
