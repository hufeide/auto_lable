# Bash 脚本参数传递说明

## 工作原理

Bash 脚本通过**环境变量**接收参数，而不是像 Python 那样使用 `--key value` 格式。

## 参数传递方式

### 在界面配置中

```json
{
  "shared_params": {
    "base_model": "/path/to/model",
    "dataset_dir": "/path/to/dataset",
    "base_dir": "/path/to/output"
  },
  "tasks": [
    {
      "id": "task6",
      "name": "模型微调",
      "script": "train_step6.sh",
      "script_type": "bash",
      "params": {},
      "use_shared_params": ["base_model", "dataset_dir", "base_dir"]
    }
  ]
}
```

### 在 Bash 脚本中接收

系统会自动将参数设置为环境变量，提供两种命名方式：
1. **原始名称**：`base_model`, `dataset_dir`, `base_dir`
2. **大写名称**：`BASE_MODEL`, `DATASET_DIR`, `BASE_DIR`

#### 推荐写法

```bash
#!/bin/bash

# 从环境变量接收参数（支持多种命名方式）
Base_model="${BASE_MODEL:-${base_model}}"
Datasetdir="${DATASET_DIR:-${dataset_dir}}"
BASE_DIR="${BASE_DIR:-${base_dir}}"

# 打印接收到的参数
echo "接收到的参数:"
echo "  Base_model: ${Base_model}"
echo "  Datasetdir: ${Datasetdir}"
echo "  BASE_DIR: ${BASE_DIR}"

# 检查必需参数
if [ -z "$Base_model" ]; then
    echo "错误: 缺少 base_model 参数"
    exit 1
fi

# 使用参数
echo "开始处理..."
echo "模型路径: ${Base_model}"
```

## 日期变量

配置中可以使用日期变量，会自动替换：

```json
{
  "shared_params": {
    "output_dir": "/path/to/output/{TODAY_COMPACT}",
    "log_file": "/path/to/logs/{TODAY}.log"
  }
}
```

### 支持的日期变量

- `{TODAY}`: 今天日期 YYYY-MM-DD (例如: 2024-11-23)
- `{TODAY_COMPACT}`: 今天日期 YYYYMMDD (例如: 20241123)
- `{TIMESTAMP}`: 当前时间戳 (例如: 1700558400)
- `{YEAR}`: 当前年份 (例如: 2024)
- `{MONTH}`: 当前月份 (例如: 11)
- `{DAY}`: 当前日期 (例如: 23)

### 示例

**配置：**
```json
{
  "shared_params": {
    "base_dir": "/home/user/output/{TODAY_COMPACT}"
  }
}
```

**实际传递给脚本：**
```bash
BASE_DIR="/home/user/output/20241123"
base_dir="/home/user/output/20241123"
```

## 完整示例

### config.json

```json
{
  "shared_params": {
    "base_model": "/home/aixz/models/qwen3vl",
    "dataset_dir": "/home/aixz/data/train.jsonl",
    "base_dir": "/home/aixz/output/{TODAY_COMPACT}",
    "gpu_id": "0"
  },
  "tasks": [
    {
      "id": "train",
      "name": "模型训练",
      "script": "/path/to/train.sh",
      "script_type": "bash",
      "params": {
        "epochs": "10"
      },
      "use_shared_params": ["base_model", "dataset_dir", "base_dir", "gpu_id"]
    }
  ]
}
```

### train.sh

```bash
#!/bin/bash

# 接收参数
BASE_MODEL="${BASE_MODEL:-${base_model}}"
DATASET_DIR="${DATASET_DIR:-${dataset_dir}}"
OUTPUT_DIR="${BASE_DIR:-${base_dir}}"
GPU_ID="${GPU_ID:-${gpu_id:-0}}"
EPOCHS="${EPOCHS:-${epochs:-5}}"

echo "训练参数:"
echo "  模型: ${BASE_MODEL}"
echo "  数据集: ${DATASET_DIR}"
echo "  输出: ${OUTPUT_DIR}"
echo "  GPU: ${GPU_ID}"
echo "  轮数: ${EPOCHS}"

# 创建输出目录
mkdir -p "${OUTPUT_DIR}"

# 开始训练
CUDA_VISIBLE_DEVICES=${GPU_ID} python train.py \
    --model "${BASE_MODEL}" \
    --data "${DATASET_DIR}" \
    --output "${OUTPUT_DIR}" \
    --epochs "${EPOCHS}"

echo "训练完成！"
```

## 调试技巧

### 1. 在脚本开头打印所有环境变量

```bash
#!/bin/bash

echo "所有环境变量:"
env | grep -E "(BASE_|base_|DATASET|dataset|DIR|dir)" | sort

echo ""
echo "接收到的参数:"
echo "  base_model: ${base_model}"
echo "  BASE_MODEL: ${BASE_MODEL}"
```

### 2. 查看服务器日志

运行任务后，查看 Flask 服务器的终端输出，会显示：
```
Bash 脚本环境变量:
  BASE_MODEL=/path/to/model
  DATASET_DIR=/path/to/dataset
  BASE_DIR=/path/to/output
```

### 3. 手动测试脚本

```bash
# 设置环境变量
export base_model="/path/to/model"
export dataset_dir="/path/to/dataset"
export base_dir="/path/to/output"

# 运行脚本
bash train.sh
```

## 常见问题

### Q: 参数没有传递到脚本中？
A: 检查以下几点：
1. 配置中是否设置了 `use_shared_params`
2. 脚本中是否正确读取环境变量
3. 查看服务器日志确认参数是否设置

### Q: 变量名大小写问题？
A: 系统会同时设置两种格式：
- 原始名称：`base_model`
- 大写名称：`BASE_MODEL`

在脚本中使用 `${BASE_MODEL:-${base_model}}` 兼容两种格式。

### Q: 如何传递数组或复杂数据？
A: 环境变量只能传递字符串。如果需要传递复杂数据：
1. 使用 JSON 字符串
2. 在脚本中解析：`echo "$DATA" | jq -r '.field'`

### Q: 日期变量不生效？
A: 确保使用正确的格式：`{TODAY_COMPACT}` 而不是 `$TODAY_COMPACT`

## 对比：Python vs Bash

### Python 脚本
```python
# 通过 argparse 接收参数
parser.add_argument('--base_model', type=str)
args = parser.parse_args()
print(args.base_model)
```

**命令行：**
```bash
python script.py --base_model /path/to/model
```

### Bash 脚本
```bash
# 通过环境变量接收参数
BASE_MODEL="${BASE_MODEL:-${base_model}}"
echo "${BASE_MODEL}"
```

**命令行：**
```bash
base_model="/path/to/model" bash script.sh
# 或
export base_model="/path/to/model"
bash script.sh
```

## 最佳实践

1. **使用环境变量**：Bash 脚本统一使用环境变量接收参数
2. **兼容多种命名**：使用 `${VAR1:-${var2}}` 语法兼容不同命名
3. **参数验证**：在脚本开头检查必需参数
4. **打印参数**：在脚本开头打印接收到的参数，便于调试
5. **使用日期变量**：利用 `{TODAY_COMPACT}` 等变量自动生成日期
