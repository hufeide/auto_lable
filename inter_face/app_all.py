#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 程序执行界面
支持配置多个按钮运行不同的 Python 程序，支持参数配置和程序间参数共享
"""

from flask import Flask, render_template, request, jsonify
import subprocess
import os
import json
import threading
from datetime import datetime

app = Flask(__name__)

# 存储任务执行状态
task_status = {}
# 存储共享参数
shared_params = {}

# 配置文件路径
CONFIG_FILE = '/home/aixz/data/hxf/ai_check/lablestudio/inter_face/config_all.json'


def recursive_format(obj, variables):
    """支持字典 / 列表 / 字符串 的递归变量替换"""
    if isinstance(obj, dict):
        return {k: recursive_format(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_format(i, variables) for i in obj]
    elif isinstance(obj, str):
        try:
            return obj.format(**variables)
        except KeyError:
            return obj
    return obj


def apply_shared_params(config):
    shared = config.get("shared_params", {})
    tasks = config.get("tasks", [])
    # ---- 1) 自动生成 TODAY_COMPACT ----
    today = datetime.now().strftime("%Y-%m-%d")
    shared["TODAY_COMPACT"] = today
    shared["Base_dir"] = os.path.join("/home/aixz/data/hxf/data/label_studio_data/", today)
    shared["Dataset_dir"] = os.path.join(shared["Base_dir"], shared["exam_id"]+"_"+shared["subject_id"]+"_"+shared["question_num"],"qwen3vl_add_begin.jsonl" )

    # ---- 2) 格式化 shared_params（包括 Datasetdir 和 BASE_DIR） ----
    shared = recursive_format(shared, shared)
    config["shared_params"] = shared
    
    for task in tasks:
        # 获取该任务声明要使用的共享参数 Key 列表
        use_keys = task.get("use_shared_params", [])
        
        # 如果任务没有 params 字典，初始化一个
        if "params" not in task:
            task["params"] = {}
            
        # 核心逻辑：将共享池中的最新值覆盖/注入到任务的 params 中
        for k in use_keys:
            if k in shared:
                task["params"][k] = shared[k]
        
        # 对任务的所有参数进行最后的格式化处理（处理路径中的变量）
        task["params"] = recursive_format(task["params"], shared)
    # ---- 3) 注入 task.params ----
    # for task in tasks:
    #     keys = task.get("use_shared_params", [])
    #     params = {k: shared[k] for k in keys if k in shared}
    #     task["params"] = recursive_format(params, shared)

    return config




def load_config():
    """加载配置文件并处理变量"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 处理配置中的变量
            # config = process_config_variables(config)
            # 3. 替换所有 {xxx}
            config = apply_shared_params(config)
            return config
    else:
        return {
            "shared_params": {
                "base_path": "/home/aixz/data/hxf/data/label_studio_data/result",
                "api_url": "http://192.168.1.210:9009/v1/chat/completions"
            },
            "tasks": [
                {
                    "id": "task1",
                    "name": "数据预处理",
                    "script": "/home/aixz/data/hxf/ai_check/lablestudio/inter_face/示例/example_script1.py",
                    "script_type": "python",
                    "params": {"input": "data.txt", "output": "result.txt"},
                    "next_task": "task2"
                },
                {
                    "id": "task2",
                    "name": "数据分析",
                    "script": "/home/aixz/data/hxf/ai_check/lablestudio/inter_face/示例/example_script2.py",
                    "script_type": "python",
                    "params": {"mode": "process"},
                    "next_task": "task3"
                },
                {
                    "id": "task3",
                    "name": "Bash 示例",
                    "script": "/home/aixz/data/hxf/ai_check/lablestudio/inter_face/示例/example_script.sh",
                    "script_type": "bash",
                    "params": {"message": "Hello from bash"},
                    "next_task": None
                }
            ]
        }

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def run_script(task_id, script_path, params, script_type='python'):
    """在后台运行脚本（支持 Python 和 Bash）- 实时输出"""
    try:
        task_status[task_id] = {
            'status': 'running',
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'output': '',
            'error': ''
        }
        
        # 设置环境变量（所有脚本都可以通过环境变量获取参数）
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # 确保 Python 输出不缓冲
        
        # 将所有参数设置为环境变量
        for key, value in params.items():
            # 转换为大写作为环境变量名
            env[key.upper()] = str(value)
            # 同时保留原始大小写
            env[key] = str(value)
        
        # 根据脚本类型构建命令
        if script_type == 'bash' or script_path.endswith('.sh'):
            # Bash 脚本 - 只传递脚本路径，参数通过环境变量获取
            cmd = ['bash', script_path]
            
            print(f"Bash 脚本环境变量:")
            for key in params.keys():
                print(f"  {key.upper()}={env[key.upper()]}")
        else:
            # Python 脚本 - 添加 -u 参数使输出不缓冲
            cmd = ['python', '-u', script_path]
            # 添加参数
            for key, value in params.items():
                cmd.extend([f'--{key}', str(value)])
        
        # 执行命令 - 实时读取输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
            env=env
        )
        
        # 实时读取输出
        output_lines = []
        error_lines = []
        
        # 读取 stdout
        while True:
            line = process.stdout.readline()
            if line:
                output_lines.append(line)
                task_status[task_id]['output'] = ''.join(output_lines)
            elif process.poll() is not None:
                break
        
        # 读取剩余的 stderr
        stderr = process.stderr.read()
        if stderr:
            error_lines.append(stderr)
            task_status[task_id]['error'] = ''.join(error_lines)
        
        # 等待进程结束
        process.wait()
        
        task_status[task_id]['status'] = 'completed' if process.returncode == 0 else 'failed'
        task_status[task_id]['return_code'] = process.returncode
        task_status[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        task_status[task_id]['status'] = 'failed'
        task_status[task_id]['error'] = str(e)
        task_status[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    """主页面"""
    config = load_config()
    # 初始化共享参数（如果配置文件中有的话）
    global shared_params
    if 'shared_params' in config:
        shared_params = config['shared_params']
    return render_template('index.html', config=config)

@app.route('/test')
def test_page():
    """测试页面"""
    return app.send_static_file('../test_api.html')

@app.route('/api/run_task', methods=['POST'])
def run_task():
    """运行任务"""
    try:
        data = request.json
        task_id = data.get('task_id')
        script = data.get('script')
        params = data.get('params', {})
        script_type = data.get('script_type', 'python')
        use_shared_params = data.get('use_shared_params', None)  # 可选的参数过滤列表
        
        print(f"\n{'='*50}")
        print(f"收到任务请求:")
        print(f"  任务ID: {task_id}")
        print(f"  脚本: {script}")
        print(f"  类型: {script_type}")
        print(f"  任务参数: {params}")
        
        # 合并共享参数
        if use_shared_params is not None:
            # 如果指定了 use_shared_params，只使用列表中的共享参数
            filtered_shared = {k: v for k, v in shared_params.items() if k in use_shared_params}
            merged_params = {**filtered_shared, **params}
            print(f"  使用共享参数: {use_shared_params}")
            print(f"  过滤后共享参数: {filtered_shared}")
        else:
            # 否则使用所有共享参数
            merged_params = {**shared_params, **params}
            print(f"  共享参数: {shared_params}")
        
        print(f"  最终参数: {merged_params}")
        print(f"{'='*50}\n")
        
        # 在后台线程中运行脚本
        thread = threading.Thread(target=run_script, args=(task_id, script, merged_params, script_type))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': f'任务 {task_id} 已启动'})
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/task_status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    status = task_status.get(task_id, {'status': 'not_started'})
    return jsonify(status)

@app.route('/api/shared_params', methods=['GET', 'POST'])
def handle_shared_params():
    """处理共享参数"""
    global shared_params
    
    if request.method == 'POST':
        data = request.json
        shared_params.update(data)
        return jsonify({'success': True, 'params': shared_params})
    else:
        return jsonify(shared_params)

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """处理配置"""
    if request.method == 'POST':
        config = request.json
        save_config(config)
        # 更新内存中的共享参数
        global shared_params
        if 'shared_params' in config:
            shared_params = config['shared_params']
        return jsonify({'success': True, 'message': '配置已保存'})
    else:
        config = load_config()
        return jsonify(config)

if __name__ == '__main__':
    port = 5006
    print("=" * 50)
    print("Python 程序执行界面已启动")
    print(f"访问地址: http://localhost:{port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=True)
