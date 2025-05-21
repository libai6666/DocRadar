"""
DocRadar - 路由模块
定义应用的所有路由和视图函数
"""
import os
import logging
import mimetypes
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask import session, abort, send_file, make_response

from app.core.auth import login_required, admin_required
from app.core.auth import authenticate, get_user_role, change_password as auth_change_password
from app.core.auth import get_last_login

from app.utils.document_parser import DocumentParser
from app.utils.search_engine import SearchEngine
from app.utils.storage import Storage

# 创建蓝图
main_bp = Blueprint('main', __name__)

# 初始化存储、搜索引擎
storage = Storage()
search_engine = SearchEngine()

# 模板上下文处理器，添加环境信息
@main_bp.context_processor
def inject_env():
    """向所有模板注入环境变量"""
    from app.core.config import ENV, HOST, PORT
    return dict(
        env=ENV,
        is_test_env=ENV == 'test',
        is_prod_env=ENV == 'production',
        host=HOST,
        port=PORT,
        current_year=datetime.now().year
    )

# 路由定义
@main_bp.route('/')
@login_required
def index():
    """首页路由"""
    # 获取分页和搜索参数
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('search', '')
    
    # 获取文档（带分页）
    documents_data = storage.get_all_documents(page=page, limit=limit, search_query=search)
    
    return render_template(
        'index.html', 
        documents=documents_data['documents'], 
        pagination=documents_data['pagination'],
        search_query=search
    )

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_url = request.form.get('next', '/')
        
        if authenticate(username, password):
            session['user'] = username
            flash('登录成功', 'success')
            return redirect(next_url)
        else:
            flash('用户名或密码错误', 'danger')
    
    next_url = request.args.get('next', '/')
    return render_template('login.html', next=next_url)

@main_bp.route('/logout')
def logout():
    """用户退出"""
    session.pop('user', None)
    flash('已退出登录', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/account')
@login_required
def account():
    """用户账号设置页面"""
    username = session.get('user')
    user_role = None
    last_login = None
    
    if username:
        # 获取用户角色
        user_role = get_user_role(username)
        
        # 获取上次登录时间
        last_login = get_last_login(username)
    
    return render_template(
        'account.html',
        user_role=user_role,
        last_login=last_login
    )

@main_bp.route('/account/change-password', methods=['POST'])
@login_required
def change_password():
    """修改用户密码"""
    username = session.get('user')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 验证输入
    if not all([current_password, new_password, confirm_password]):
        flash('所有字段都必须填写', 'danger')
        return redirect(url_for('main.account'))
    
    if new_password != confirm_password:
        flash('两次输入的新密码不一致', 'danger')
        return redirect(url_for('main.account'))
    
    if len(new_password) < 8:
        flash('新密码长度必须至少为8个字符', 'danger')
        return redirect(url_for('main.account'))
    
    # 验证当前密码
    if not authenticate(username, current_password):
        flash('当前密码不正确', 'danger')
        return redirect(url_for('main.account'))
    
    # 修改密码
    success = auth_change_password(username, new_password)
    
    if success:
        # 密码修改成功后，清除用户会话并重定向到登录页面
        flash('密码修改成功，请使用新密码重新登录', 'success')
        session.pop('user', None)  # 清除用户会话
        return redirect(url_for('main.login'))
    else:
        flash('密码修改失败，请稍后重试', 'danger')
        return redirect(url_for('main.account'))

# 其他路由根据功能在其他模块中定义 