# 故障排查指南

## 点击按钮没反应？

### 1. 检查浏览器控制台
打开浏览器开发者工具（F12），查看 Console 标签页是否有错误信息。

### 2. 检查 Flask 服务是否正常运行
确保终端中看到类似输出：
```
* Running on http://0.0.0.0:5000
```

### 3. 检查网络请求
在浏览器开发者工具的 Network 标签页中，点击按钮后查看是否有请求发送到 `/api/run_task`。

### 4. 使用测试配置
将 `config_test.json` 重命名为 `config.json` 来使用简单的测试配置：
```bash
cd lablestudio/inter_face
mv config.json config_backup.json
mv config_test.json config.json
python app.py
```

### 5. 手动测试脚本
在终端中手动运行脚本，确保脚本本身没有问题：
```bash
# 测试 Python 脚本
python test_script1.py --exam_id 475 --subject_id 2119

# 测试 Bash 脚本
bash ../example_script.sh "Hello" "3"
```

### 6. 检查脚本路径
确保 config.json 中的脚本路径正确。路径是相对于 `inter_face` 目录的。

### 7. 查看服务器日志
点击按钮后，查看运行 Flask 的终端窗口，应该会看到：
```
==================================================
收到任务请求:
  任务ID: task1
  脚本: test_script1.py
  类型: python
  参数: {...}
==================================================
```

## 常见问题

### Q: 脚本路径找不到
A: 检查 config.json 中的路径，确保相对于 `inter_face` 目录正确。

### Q: Python 脚本报错
A: 确保脚本使用 argparse 接收参数，参数名要匹配。

### Q: Bash 脚本没有输出
A: Bash 脚本通过环境变量接收参数，使用 `$PARAM_NAME` 格式（大写）。

### Q: 任务一直显示"运行中"
A: 检查脚本是否正常退出，或者是否有死循环。

## 快速测试

运行以下命令进行快速测试：
```bash
cd lablestudio/inter_face

# 测试 Python 脚本
python test_script1.py --exam_id 123 --subject_id 456

# 启动服务
bash start.sh
```

然后访问 http://localhost:5000，点击"测试任务1"按钮。
