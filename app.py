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
    from app.core.config import HOST, PORT, DEBUG, CURRENT_IP
    
    # 打印实际IP地址信息
    print(f"应用已启动，绑定地址: {HOST}:{PORT}")
    print(f"您可以通过以下地址访问应用:")
    print(f"- 本地访问: http://127.0.0.1:{PORT}/")
    print(f"- 局域网访问: http://{CURRENT_IP}:{PORT}/")
    
    # 运行应用
    app.run(host=HOST, port=PORT, debug=DEBUG)

if __name__ == '__main__':
    main()