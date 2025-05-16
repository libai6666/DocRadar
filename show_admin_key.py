#!/usr/bin/env python
"""
查看和设置ADMIN_KEY
用法: 
- 查看当前ADMIN_KEY: python show_admin_key.py
- 设置新ADMIN_KEY: python show_admin_key.py --set NEW_KEY
- 生成随机ADMIN_KEY并保存: python show_admin_key.py --generate
"""
import os
import sys
import json
import argparse
import secrets

# 获取应用根目录
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

# 配置文件路径
ADMIN_CONFIG_PATH = os.path.join(BASE_DIR, 'admin_config.json')

def read_admin_config():
    """读取管理员配置"""
    if os.path.exists(ADMIN_CONFIG_PATH):
        try:
            with open(ADMIN_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    return {}

def write_admin_config(config_data):
    """写入管理员配置"""
    try:
        with open(ADMIN_CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=2)
        print(f"配置已保存到 {ADMIN_CONFIG_PATH}")
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False

def show_current_key():
    """显示当前ADMIN_KEY"""
    config_data = read_admin_config()
    file_key = config_data.get('ADMIN_KEY')
    env_key = os.environ.get('DOCRADAR_ADMIN_KEY')
    
    if file_key:
        print(f"ADMIN_KEY (从配置文件): {file_key}")
        print(f"\n配置文件路径: {ADMIN_CONFIG_PATH}")
    elif env_key:
        print(f"ADMIN_KEY (从环境变量): {env_key}")
        print("\n要将此值保存到配置文件, 执行:")
        print(f"python show_admin_key.py --set {env_key}")
    else:
        # 使用与应用相同的逻辑生成密钥
        random_key = secrets.token_hex(8)
        print(f"ADMIN_KEY (随机生成): {random_key}")
        print("\n注意: 这个密钥会在每次应用重启时改变。")
        print("要设置一个固定密钥, 请执行以下任一操作:")
        print(f"1. 保存到配置文件: python show_admin_key.py --set {random_key}")
        print('2. 设置环境变量: set DOCRADAR_ADMIN_KEY="your-key"')
        
    print('\n访问数据库管理页面的URL:')
    key_to_use = file_key or env_key or secrets.token_hex(8)
    print(f'http://localhost:5000/admin/db?key={key_to_use}')

def set_admin_key(key):
    """设置ADMIN_KEY到配置文件"""
    config_data = read_admin_config()
    config_data['ADMIN_KEY'] = key
    if write_admin_config(config_data):
        print(f"ADMIN_KEY 已设置为: {key}")
        print('\n访问数据库管理页面的URL:')
        print(f'http://localhost:5000/admin/db?key={key}')

def generate_and_save_key():
    """生成随机密钥并保存"""
    new_key = secrets.token_hex(8)
    set_admin_key(new_key)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='查看和设置ADMIN_KEY')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--set', metavar='KEY', help='设置新的ADMIN_KEY')
    group.add_argument('--generate', action='store_true', help='生成随机ADMIN_KEY并保存')
    
    args = parser.parse_args()
    
    if args.set:
        set_admin_key(args.set)
    elif args.generate:
        generate_and_save_key()
    else:
        show_current_key()

if __name__ == "__main__":
    main() 