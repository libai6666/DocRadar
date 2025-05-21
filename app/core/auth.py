"""
DocRadar - 用户认证模块
提供基本的用户登录和访问控制功能
"""
import os
import json
from functools import wraps
from flask import request, redirect, url_for, flash, session, abort
import hashlib
import secrets
from datetime import datetime
from app.core.config import ENV, ROOT_DIR

def get_config_path(filename):
    """获取配置文件路径"""
    return os.path.join(ROOT_DIR, 'config', filename)

# 根据环境设置用户数据文件
if ENV == 'production':
    USERS_FILE = os.environ.get('USERS_FILE', get_config_path('users_production.json'))
else:  # test
    USERS_FILE = os.environ.get('USERS_FILE', get_config_path('users_test.json'))

def init_users():
    """初始化用户文件，如果不存在则创建默认管理员账户"""
    if not os.path.exists(USERS_FILE):
        # 创建默认admin用户，密码为随机生成
        default_password = 'password' if ENV == 'test' else secrets.token_urlsafe(8)
        default_password_hash = hashlib.sha256(default_password.encode()).hexdigest()
        
        users = {
            "admin": {
                "password_hash": default_password_hash,
                "role": "admin",
                "last_login": None
            }
        }
        
        # 如果是测试环境，添加一个测试用户
        if ENV == 'test':
            users["test_user"] = {
                "password_hash": default_password_hash,
                "role": "user",
                "last_login": None
            }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
            
        print(f"创建默认管理员账户: admin / {default_password}")
        print("请登录后立即修改密码")
        
        return True
    return False

def get_users():
    """获取所有用户信息"""
    if not os.path.exists(USERS_FILE):
        init_users()
        
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    """保存用户信息"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)

def authenticate(username, password):
    """验证用户身份"""
    users = get_users()
    if username in users:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if users[username]["password_hash"] == password_hash:
            # 记录登录时间
            update_last_login(username)
            return True
    return False

def update_last_login(username):
    """更新用户最后登录时间"""
    users = get_users()
    if username in users:
        # 使用UTC+8时间（北京时间）
        users[username]["last_login"] = (datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        save_users(users)
        return True
    return False

def get_last_login(username):
    """获取用户最后登录时间"""
    users = get_users()
    if username in users and "last_login" in users[username]:
        return users[username]["last_login"]
    return None

def get_user_role(username):
    """获取用户角色"""
    users = get_users()
    if username in users:
        return users[username].get("role", "user")
    return None

def login_required(f):
    """登录要求装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限要求装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('main.login', next=request.url))
        
        username = session['user']
        role = get_user_role(username)
        
        if role != 'admin':
            abort(403)
            
        return f(*args, **kwargs)
    return decorated_function

def change_password(username, new_password):
    """修改用户密码"""
    users = get_users()
    if username in users:
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        users[username]["password_hash"] = password_hash
        save_users(users)
        return True
    return False

def add_user(username, password, role="user"):
    """添加新用户"""
    users = get_users()
    if username in users:
        return False
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    users[username] = {
        "password_hash": password_hash,
        "role": role,
        "last_login": None
    }
    save_users(users)
    return True

def delete_user(username):
    """删除用户"""
    users = get_users()
    if username in users:
        del users[username]
        save_users(users)
        return True
    return False 