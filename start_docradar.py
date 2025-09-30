#!/usr/bin/env python
"""
DocRadar启动辅助脚本
自动检测当前IP地址并启动应用
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # 获取项目根目录
    root_dir = Path(__file__).parent.absolute()
    
    # 解析命令行参数
    env = 'test'  # 默认环境
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ('--env', '-e') and i + 1 < len(args):
            env = args[i + 1]
            i += 2
        else:
            i += 1
    
    # 验证环境参数
    if env not in ('test', 'production'):
        print(f"错误：无效的环境参数 '{env}'，必须是 'test' 或 'production'")
        sys.exit(1)
    
    print(f"准备在 {env} 环境中启动 DocRadar...")
    
    # 1. 运行IP配置工具，检测并更新当前IP
    print("正在检测当前IP地址...")
    ip_config_script = root_dir / "utils" / "ip_config.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(ip_config_script)],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"IP配置更新失败: {e}")
        print(f"错误输出: {e.stderr}")
        sys.exit(1)
    
    # 2. 启动应用
    print(f"正在启动DocRadar应用 ({env}环境)...")
    app_script = root_dir / "app.py"
    
    try:
        # 设置环境变量
        env_vars = os.environ.copy()
        env_vars['DOCRADAR_ENV'] = env
        
        # 使用当前Python解释器运行app.py
        subprocess.run(
            [sys.executable, str(app_script), '-e', env],
            env=env_vars,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n应用已停止")

if __name__ == "__main__":
    main()
