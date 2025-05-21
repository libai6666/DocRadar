#!/usr/bin/env python
"""
查看和设置ADMIN_KEY
用法: 
- 查看当前ADMIN_KEY: python show_admin_key.py [--env production|test]
- 设置新ADMIN_KEY: python show_admin_key.py --set NEW_KEY [--env production|test]
- 生成随机ADMIN_KEY并保存: python show_admin_key.py --generate [--env production|test]
- 重置管理员密码: python show_admin_key.py --reset-admin-password [--env production|test]
"""
import os
import sys
import json
import argparse
import secrets
import hashlib

# 获取应用根目录
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

def get_admin_config_path(env):
    """根据环境获取管理员配置文件路径"""
    if env == 'production':
        return os.path.join(BASE_DIR, 'admin_config_production.json')
    else:  # test
        return os.path.join(BASE_DIR, 'admin_config_test.json')

def get_users_file_path(env):
    """根据环境获取用户文件路径"""
    if env == 'production':
        return os.path.join(BASE_DIR, 'users_production.json')
    else:  # test
        return os.path.join(BASE_DIR, 'users_test.json')

def read_admin_config(env):
    """读取管理员配置"""
    admin_config_path = get_admin_config_path(env)
    if os.path.exists(admin_config_path):
        try:
            with open(admin_config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    return {}

def write_admin_config(config_data, env):
    """写入管理员配置"""
    admin_config_path = get_admin_config_path(env)
    try:
        with open(admin_config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        print(f"配置已保存到 {admin_config_path}")
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False

def read_users_file(env):
    """读取用户文件"""
    users_file_path = get_users_file_path(env)
    if os.path.exists(users_file_path):
        try:
            with open(users_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取用户文件失败: {e}")
    return {}

def write_users_file(users_data, env):
    """写入用户文件"""
    users_file_path = get_users_file_path(env)
    try:
        with open(users_file_path, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=4)
        print(f"用户数据已保存到 {users_file_path}")
        return True
    except Exception as e:
        print(f"保存用户文件失败: {e}")
        return False

def reset_admin_password(env):
    """重置管理员密码"""
    # 生成新的随机密码
    new_password = secrets.token_urlsafe(8)
    # 计算密码哈希
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    
    # 读取用户文件
    users = read_users_file(env)
    
    # 更新admin用户密码
    if "admin" in users:
        users["admin"]["password_hash"] = password_hash
        if write_users_file(users, env):
            print(f"管理员密码已重置: admin / {new_password}")
            print("请登录后立即修改密码")
            
            # 提供登录地址
            if env == 'production':
                login_url = 'http://192.168.0.110:5000/login'
            else:
                login_url = 'http://127.0.0.1:5000/login'
            print(f"登录地址: {login_url}")
            
            return True
    else:
        # 如果admin用户不存在，创建一个新的admin用户
        print("警告: 用户文件中没有admin用户，将创建新的admin用户")
        users["admin"] = {
            "password_hash": password_hash,
            "role": "admin",
            "last_login": None
        }
        if write_users_file(users, env):
            print(f"已创建新的管理员账户: admin / {new_password}")
            print("请登录后立即修改密码")
            
            # 提供登录地址
            if env == 'production':
                login_url = 'http://192.168.0.110:5000/login'
            else:
                login_url = 'http://127.0.0.1:5000/login'
            print(f"登录地址: {login_url}")
            
            return True
    
    return False

def ensure_config_files_exist(env):
    """确保配置文件存在"""
    # 确保admin_config文件存在
    admin_config_path = get_admin_config_path(env)
    if not os.path.exists(admin_config_path):
        # 创建新的admin_config文件
        new_key = secrets.token_hex(8)
        config_data = {"ADMIN_KEY": new_key}
        with open(admin_config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        print(f"已创建新的管理员配置文件: {admin_config_path}")
    
    # 确保users文件存在
    users_file_path = get_users_file_path(env)
    if not os.path.exists(users_file_path):
        # 创建默认admin用户
        default_password = 'password' if env == 'test' else secrets.token_urlsafe(8)
        password_hash = hashlib.sha256(default_password.encode()).hexdigest()
        
        users = {
            "admin": {
                "password_hash": password_hash,
                "role": "admin",
                "last_login": None
            }
        }
        
        # 如果是测试环境，添加一个测试用户
        if env == 'test':
            users["test_user"] = {
                "password_hash": password_hash,
                "role": "user",
                "last_login": None
            }
        
        with open(users_file_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
        
        print(f"已创建新的用户文件: {users_file_path}")
        print(f"默认管理员账户: admin / {default_password}")
        print("请登录后立即修改密码")

def show_current_key(env):
    """显示当前ADMIN_KEY"""
    # 确保配置文件存在
    ensure_config_files_exist(env)
    
    config_data = read_admin_config(env)
    file_key = config_data.get('ADMIN_KEY')
    env_key = os.environ.get('ADMIN_KEY')
    
    print(f"当前环境: {env}")
    
    if file_key:
        print(f"ADMIN_KEY (从配置文件): {file_key}")
        print(f"\n配置文件路径: {get_admin_config_path(env)}")
    elif env_key:
        print(f"ADMIN_KEY (从环境变量): {env_key}")
        print("\n要将此值保存到配置文件, 执行:")
        print(f"python show_admin_key.py --set {env_key} --env {env}")
    else:
        # 使用与应用相同的逻辑生成密钥
        random_key = secrets.token_hex(8)
        print(f"ADMIN_KEY (随机生成): {random_key}")
        print("\n注意: 这个密钥会在每次应用重启时改变。")
        print("要设置一个固定密钥, 请执行以下任一操作:")
        print(f"1. 保存到配置文件: python show_admin_key.py --set {random_key} --env {env}")
        print('2. 设置环境变量: set ADMIN_KEY="your-key"')
        
    print('\n访问数据库管理页面的URL:')
    key_to_use = file_key or env_key or secrets.token_hex(8)
    if env == 'production':
        print(f'http://192.168.0.110:5000/admin/db?key={key_to_use}')
    else:
        print(f'http://127.0.0.1:5000/admin/db?key={key_to_use}')

def set_admin_key(key, env):
    """设置ADMIN_KEY到配置文件"""
    # 确保配置文件存在
    ensure_config_files_exist(env)
    
    config_data = read_admin_config(env)
    config_data['ADMIN_KEY'] = key
    if write_admin_config(config_data, env):
        print(f"ADMIN_KEY 已设置为: {key}")
        print('\n访问数据库管理页面的URL:')
        if env == 'production':
            print(f'http://192.168.0.110:5000/admin/db?key={key}')
        else:
            print(f'http://127.0.0.1:5000/admin/db?key={key}')

def generate_and_save_key(env):
    """生成随机密钥并保存"""
    new_key = secrets.token_hex(8)
    set_admin_key(new_key, env)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='查看和设置ADMIN_KEY')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--set', metavar='KEY', help='设置新的ADMIN_KEY')
    group.add_argument('--generate', action='store_true', help='生成随机ADMIN_KEY并保存')
    group.add_argument('--reset-admin-password', action='store_true', help='重置管理员密码')
    parser.add_argument('--env', choices=['production', 'test'], default='test', help='指定环境 (默认: test)')
    
    args = parser.parse_args()
    
    if args.set:
        set_admin_key(args.set, args.env)
    elif args.generate:
        generate_and_save_key(args.env)
    elif args.reset_admin_password:
        reset_admin_password(args.env)
    else:
        show_current_key(args.env)

if __name__ == "__main__":
    main() 