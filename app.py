#!/usr/bin/env python
"""
DocRadar 启动脚本
使用方法：
    python app.py -e test      # 运行测试环境（默认）
    python app.py -e production # 运行生产环境
"""

import os
import sys

def main():
    # 默认参数
    env = 'test'
    
    # 解析命令行参数
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
    
    # 设置环境变量
    os.environ['DOCRADAR_ENV'] = env
    
    # 打印运行信息
    print(f"正在 {env} 环境中启动 DocRadar...")
    
    # 导入并运行应用
    from app import app
    
    # 根据环境设置主机和端口
    from app.core.config import HOST, PORT, DEBUG
    
    # 运行应用
    app.run(host=HOST, port=PORT, debug=DEBUG)

if __name__ == '__main__':
    main()