# Python 程序执行界面

一个功能强大的 Web 界面，用于配置和运行 Python/Bash 程序。

## ✨ 功能特性

- ✅ **按钮式执行**: 点击按钮运行配置好的程序
- ✅ **支持多种脚本**: Python 和 Bash 脚本
- ✅ **参数配置**: 为每个程序配置独立的运行参数
- ✅ **参数共享**: 在多个程序间共享参数
- ✅ **任务链**: 一个任务完成后自动提示运行下一个
- ✅ **实时状态**: 实时显示任务运行状态和输出
- ✅ **美观界面**: 现代化的渐变色设计

## 🚀 快速开始

### 方式1: 使用启动脚本（推荐）
```bash
cd lablestudio/inter_face
bash run.sh
```

### 方式2: 直接运行
```bash
cd lablestudio/inter_face
python app.py
```

然后在浏览器中访问: **http://localhost:5001**

## 📁 文件结构

```
inter_face/
├── app.py                  # Flask 后端服务
├── config.json             # 任务配置文件
├── test_script1.py         # Python 测试脚本
├── run.sh                  # 快速启动脚本
├── templates/
│   └── index.html          # 前端界面
├── 使用说明.md             # 详细使用说明
└── TROUBLESHOOTING.md      # 故障排查指南
```

## ⚙️ 配置任务

编辑 `config.json` 文件：

```json
{
  "tasks": [
    {
      "id": "task1",
      "name": "错误数据查询",
      "script": "/path/to/your/script.py",
      "script_type": "python",
      "params": {
        "exam_id": "475",
        "subject_id": "2119"
      },
      "next_task": "task2"
    }
  ]
}
```

### 配置说明

- **id**: 任务唯一标识符
- **name**: 任务显示名称
- **script**: 脚本文件路径（绝对路径或相对路径）
- **script_type**: 脚本类型 (`python` 或 `bash`)
- **params**: 运行参数（键值对）
- **next_task**: 下一个任务的 id（可选）

## 📝 编写脚本

### Python 脚本示例

```python
#!/usr/bin/env python3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='你的脚本')
    parser.add_argument('--exam_id', type=str, help='考试ID')
    parser.add_argument('--subject_id', type=str, help='科目ID')
    args = parser.parse_args()
    
    print(f"考试ID: {args.exam_id}")
    print(f"科目ID: {args.subject_id}")
    
    # 你的代码逻辑
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

### Bash 脚本示例

```bash
#!/bin/bash

# 参数通过环境变量传递（自动转为大写）
echo "考试ID: $EXAM_ID"
echo "科目ID: $SUBJECT_ID"

# 你的代码逻辑

exit 0
```

## 🎯 使用界面

1. **添加共享参数**（可选）
   - 在顶部输入参数名和值
   - 点击"添加参数"
   - 共享参数会应用到所有任务

2. **运行任务**
   - 点击任务卡片上的"运行任务"按钮
   - 查看实时状态和输出
   - 任务完成后可以重新运行

3. **任务链执行**
   - 如果配置了 `next_task`
   - 任务完成后会自动提示运行下一个

## 🔧 API 接口

### 运行任务
```bash
POST /api/run_task
Content-Type: application/json

{
  "task_id": "task1",
  "script": "script.py",
  "params": {"key": "value"},
  "script_type": "python"
}
```

### 查看任务状态
```bash
GET /api/task_status/{task_id}
```

### 管理共享参数
```bash
# 获取
GET /api/shared_params

# 设置
POST /api/shared_params
Content-Type: application/json

{"param_name": "param_value"}
```

## 🐛 故障排查

### 点击按钮没反应？

1. 打开浏览器开发者工具（F12）查看 Console
2. 检查服务器终端是否有错误日志
3. 访问测试页面: http://localhost:5001/test
4. 查看详细排查步骤: `TROUBLESHOOTING.md`

### 脚本执行失败？

1. 手动运行脚本确保脚本本身没问题
2. 检查脚本路径是否正确
3. 确保 Python 脚本使用 argparse 接收参数
4. 确保 Bash 脚本有执行权限

## 📦 依赖

```bash
pip install Flask
```

## 🎨 界面预览

- 渐变色设计
- 响应式布局
- 实时状态更新
- 任务输出显示
- 错误信息提示

## 📞 当前状态

✅ 服务已启动: http://localhost:5001
✅ API 测试通过
✅ 支持 Python 和 Bash 脚本
✅ 示例脚本可用

## 💡 提示

- 使用绝对路径避免路径问题
- Python 脚本必须使用 argparse
- Bash 脚本参数通过环境变量（大写）
- 查看服务器日志了解详细信息

---

现在可以开始使用了！访问 http://localhost:5001
