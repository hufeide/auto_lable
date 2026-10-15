
#!/bin/bash

# 从环境变量接收参数（由界面传递）
# 支持多种命名方式
Base_model="$BASE_MODEL"
# Dataset_dir="$DATASET_DIR"
# echo "Dataset_dir: ${Dataset_dir}"
# Dataset_dir=("${DATASET_DIR[@]}")
Base_dir="$BASE_DIR"
# 2. 检查并创建目录
mkdir -p "$Base_dir"

# 拼接成 "['路径']" 格式
DATASET_DIR="['$DATASET_DIR']"

echo "$DATASET_DIR"
# DATASET_DIR="['/home/aixz/data/hxf/data/label_studio_data/2025-11-21/475_2119_24/qwen3vl_add_begin.jsonl']"
DATASET_DIR_CLEANED=$(echo "$DATASET_DIR" | tr "'" '"')

# 3. 使用 jq 解析 JSON 数组，-r 确保输出不带引号，.[] 将每个元素输出到新行
# 4. 使用 $() 命令替换和圆括号 () 将 jq 的输出（以换行符分隔）赋值给 Bash 数组
if command -v jq &> /dev/null; then
    Dataset_dir=($(echo "$DATASET_DIR_CLEANED" | jq -r '.[]'))
    
    echo "================================"
    echo "✅ 修正后的 Dataset_dir 数组元素:"
    echo "${Dataset_dir[@]}"
else
    echo "❌ 错误: 未找到 'jq' 命令。"
fi
# echo "$DATASET_DIR"
# eval "Dataset_dir=($(echo "$DATASET_DIR" | jq -r '.[] | @sh'))"
# 打印接收到的参数
echo "================================"
echo "接收到的参数:"
echo "  Base_model: ${Base_model}"
echo "  Dataset_dir: ${Dataset_dir}"
echo "  Base_dir: ${Base_dir}"
echo "================================"
echo ""

# 检查必需参数
if [ -z "$Base_model" ] || [ -z "$Dataset_dir" ] || [ -z "$Base_dir" ]; then
    echo "错误: 缺少必需参数"
    echo "需要的环境变量:"
    echo "  BASE_MODEL 或 base_model: 基础模型路径"
    echo "  DATASET_DIR 或 dataset_dir: 数据集路径"
    echo "  Base_dir 或 Base_dir: 输出目录"
    exit 1
fi

# export Base_model=/home/aixz/data/hxf/bigmodel/my_latex_qwen2.5vl/output_Qwen3vl/20251115/merged_qwen3vl_1115_2/
# export Dataset_dir="('/home/aixz/data/hxf/data/label_studio_data/2025-11-21/475_2119_24/qwen3vl_add_begin.jsonl')"
# export Base_dir=/home/aixz/data/hxf/data/label_studio_data/model/2025-11-21
# echo "${Dataset_dir[@]}"
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    echo "警告: 未找到 conda base 环境。尝试通过默认路径初始化..."
    # 尝试常见的默认路径
    if [ -f "/home/aixz/anaconda3/etc/profile.d/conda.sh" ]; then
        source "/home/aixz/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        source "/opt/conda/etc/profile.d/conda.sh"
    else
        echo "错误: 无法自动初始化 conda。请手动检查安装。"
        exit 1
    fi
else
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    echo "已成功从 $CONDA_BASE 初始化 conda."
fi
echo ""

echo "--- 正在激活 conda 环境 'unsloth_env'开始训练 ---"
conda activate unsloth_env

echo "开始训练..."
echo "  模型: ${Base_model}"
echo "  数据集: ${Dataset_dir}"
echo "  输出目录: ${Base_dir}"
echo ""
PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True' \
CUDA_VISIBLE_DEVICES=2 \
swift sft \
    --model "${Base_model}"\
    --dataset "${Dataset_dir[@]}"\
    --load_from_cache_file true \
    --split_dataset_ratio 0.01 \
    --train_type lora \
    --torch_dtype bfloat16 \
    --num_train_epochs 2 \
    --per_device_train_batch_size 4 \
    --per_device_eval_batch_size 4 \
    --gradient_accumulation_steps 2 \
    --attn_impl flash_attn \
    --padding_free true \
    --learning_rate 1e-5 \
    --lora_rank 32 \
    --lora_alpha 64 \
    --target_modules all-linear \
    --freeze_vit False \
    --freeze_aligner False \
    --packing False \
    --eval_steps 200 \
    --save_steps 200 \
    --save_total_limit 3 \
    --logging_steps 15 \
    --max_length 2048 \
    --output_dir "${Base_dir}" \
    --dataset_num_proc 10 \
    --dataloader_num_workers 10 \
    --max_grad_norm 1 \
    --warmup_ratio 0.02


# Base_model="/home/aixz/data/hxf/bigmodel/my_latex_qwen2.5vl/output_Qwen3vl/20251115/merged_qwen3vl_1115_2/"
LATEST_VERSION_DIR=$(ls -d "${Base_dir}"/v*-* 2>/dev/null | sort | tail -n 1)
if [ -z "$LATEST_VERSION_DIR" ]; then
    echo "错误：在 ${Base_dir} 中未找到版本目录 (v*-*)。"
    exit 1
fi
echo "找到最新的版本目录: $(basename "${LATEST_VERSION_DIR}")"

ADAPTERS_PATH=$(ls -d "${LATEST_VERSION_DIR}"/checkpoint-* 2>/dev/null | sort -V | tail -n 1)
if [ -z "$ADAPTERS_PATH" ]; then
    echo "错误：在目录 ${LATEST_VERSION_DIR} 中未找到检查点目录。"
    exit 1
fi
echo "${ADAPTERS_PATH}"
TODAY_COMPACT=$(date +%Y%m%d)
OUTPUT_PATH="${Base_dir}/merged_qwen3vl_${TODAY_COMPACT}"


rm -rf "${OUTPUT_PATH}"
echo "--- 训练完成，开始导出模型 ---"
CUDA_VISIBLE_DEVICES=2 \
swift export \
    --adapters "${ADAPTERS_PATH}" \
    --merge_lora true \
    --output_dir "${OUTPUT_PATH}"





# OUTPUT_PATH="/home/aixz/data/hxf/bigmodel/my_latex_qwen2.5vl/output_Qwen3vl/20251116/merged_qwen3vl_1116_1"
# PORT=${1:-9025}
# LOG_DIR="./log"
# LOG_FILE="${LOG_DIR}/stop-console.log"

echo "导出完成，正在查找正在运行的进程（端口 9025）..."

# 使用端口查找对应PID
PID=$(lsof -t -i:9025)

if [ -z "$PID" ]; then
    echo "没有找到正在运行的进程"
else
    echo "找到进程 PID: $PID，正在结束中..."
    kill $PID

    # 等待进程结束
    sleep 2

    if ps -p $PID > /dev/null; then
        echo "进程仍在运行，使用 kill -9 强制结束..."
        kill -9 $PID
    fi

    echo "服务已停止"
fi

echo "--- 导出模型完成，开始启动服务 ---"
export CUDA_VISIBLE_DEVICES=2
nohup vllm serve  "${OUTPUT_PATH}"\
    --served-model-name qwen3_vl \
    --port 9025 \
    --tensor-parallel-size 1 \
    --limit-mm-per-prompt.video 0 \
    --async-scheduling \
    --gpu-memory-utilization 0.6 \
    --max-num-seqs 128 \
    --max-model-len 2048 &


