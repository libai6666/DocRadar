#!/usr/bin/env python
"""
IP配置工具 - 用于检测当前主机IP并提供给应用使用
"""

import os
import socket
import json
import logging
from pathlib import Path

def get_local_ip():
    """
    获取本地主机的IP地址
    尝试连接到一个外部服务器并获取本地IP
    如果失败则返回localhost
    """
    try:
        # 创建一个临时socket连接，用于获取本地IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 这里不需要真正建立连接，只是获取本地IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logging.warning(f"无法获取本地IP: {e}")
        # 如果无法获取IP，返回localhost
        return "127.0.0.1"

def update_env_file(ip_address=None):
    """
    更新或创建环境变量文件，存储当前IP地址
    """
    if ip_address is None:
        ip_address = get_local_ip()
    
    # 项目根目录
    root_dir = Path(__file__).parent.parent.absolute()
    env_file = root_dir / ".env"
    
    # 读取现有环境变量（如果存在）
    env_vars = {}
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    
    # 更新IP地址
    env_vars["DOCRADAR_HOST"] = ip_address
    
    # 写回文件
    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    logging.info(f"已更新环境变量文件，当前IP: {ip_address}")
    return ip_address

def update_config_files(ip_address=None):
    """
    更新配置文件中的IP地址
    """
    if ip_address is None:
        ip_address = get_local_ip()
    
    # 项目根目录
    root_dir = Path(__file__).parent.parent.absolute()
    
    # 更新app/core/config.py中的IP地址（通过环境变量，不直接修改文件）
    os.environ["DOCRADAR_HOST"] = ip_address
    
    # 记录当前IP地址到配置文件
    ip_config_file = root_dir / "config" / "ip_config.json"
    os.makedirs(ip_config_file.parent, exist_ok=True)
    
    with open(ip_config_file, "w") as f:
        json.dump({"current_ip": ip_address}, f, indent=2)
    
    logging.info(f"已更新IP配置文件，当前IP: {ip_address}")
    return ip_address

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 获取当前IP
    current_ip = get_local_ip()
    logging.info(f"当前检测到的IP地址: {current_ip}")
    
    # 更新环境变量和配置文件
    update_env_file(current_ip)
    update_config_files(current_ip)
    
    print(f"当前IP地址: {current_ip}")
    print("IP配置已更新")
