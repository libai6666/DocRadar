"""
DocRadar - 核心路由模块
提供基本的页面路由和视图函数
"""
import logging
import os
import sqlite3
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, g, jsonify, current_app
)
from werkzeug.utils import secure_filename

from app.core.auth import (
    authenticate, login_required, admin_required, get_last_login,
    get_user_role, change_password
)
from app.core.config import (
    ALLOWED_EXTENSIONS, UPLOAD_FOLDER, DATABASE_URI,
    SQLITE_CONFIG, DOCUMENT_IMAGES_DIR
)
# 文档解析器类在其他模块中使用
# from app.utils.document_parser import DocumentParser
# 搜索引擎和存储管理使用类的方式导入
from app.utils.search_engine import SearchEngine
from app.utils.storage import Storage

# 创建蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/', endpoint='index')
def home():
    """首页视图"""
    storage = Storage()
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search_query = request.args.get('search', '', type=str)
    
    # 获取日期筛选参数
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    
    # 验证日期格式（如果提供了日期）
    if start_date and not start_date.strip():
        start_date = None
    if end_date and not end_date.strip():
        end_date = None
    
    # 获取文档列表和分页信息
    try:
        result = storage.get_all_documents(
            page=page, 
            limit=limit, 
            search_query=search_query if search_query else None,
            start_date=start_date,
            end_date=end_date
        )
        documents = result.get('documents', [])
        pagination = result.get('pagination', {})
        doc_count = pagination.get('total', 0)
    except Exception as e:
        logging.error(f"获取文档列表失败: {e}")
        documents = []
        pagination = {
            'page': 1,
            'limit': 10,
            'total': 0,
            'pages': 0,
            'has_prev': False,
            'has_next': False
        }
        doc_count = 0
    
    # 搜索历史功能暂时禁用
    recent_searches = []
    
    # 获取用户角色
    role = None
    if 'user' in session:
        role = get_user_role(session['user'])
    
    return render_template(
        'index.html', 
        documents=documents,
        pagination=pagination,
        doc_count=doc_count,
        search_query=search_query,
        recent_searches=recent_searches,
        role=role,
        start_date=start_date or '',
        end_date=end_date or ''
    )

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_url = request.form.get('next', '/')
        remember_password = request.form.get('rememberPassword') == 'on'
        
        logging.info(f"登录尝试 - 用户名: {username}, 记住密码: {remember_password}")
        
        if authenticate(username, password):
            session['user'] = username
            # 添加会话诊断日志
            logging.info(f"用户 {username} 登录成功，会话ID: {session.sid if hasattr(session, 'sid') else '未知'}")
            flash('登录成功', 'success')
            return redirect(next_url)
        else:
            logging.warning(f"登录失败 - 用户名: {username}")
            flash('用户名或密码错误', 'danger')
            # 添加login_error参数，防止自动登录循环
            return redirect(url_for('main.login', login_error=1, next=next_url))
    
    next_url = request.args.get('next', '/')
    return render_template('login.html', next=next_url)

@main_bp.route('/logout')
def logout():
    """用户登出"""
    # 添加会话诊断日志
    if 'user' in session:
        username = session['user']
        session_id = session.sid if hasattr(session, 'sid') else '未知'
        logging.info(f"用户 {username} 登出，会话ID: {session_id}")
    
    # 清除会话
    session.clear()
    flash('您已成功登出', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """用户账户管理"""
    username = session['user']
    last_login = get_last_login(username)
    role = get_user_role(username)
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证当前密码
        if not authenticate(username, current_password):
            flash('当前密码不正确', 'danger')
            return redirect(url_for('main.account'))
        
        # 验证新密码
        if new_password != confirm_password:
            flash('新密码与确认密码不匹配', 'danger')
            return redirect(url_for('main.account'))
        
        # 更改密码
        if change_password(username, new_password):
            # 添加会话诊断日志
            logging.info(f"用户 {username} 修改密码成功，会话ID: {session.sid if hasattr(session, 'sid') else '未知'}")
            flash('密码已成功更改', 'success')
        else:
            flash('密码更改失败', 'danger')
        
        return redirect(url_for('main.account'))
    
    # 添加会话诊断日志
    session_id = session.sid if hasattr(session, 'sid') else '未知'
    logging.info(f"用户 {username} 访问账户页面，会话ID: {session_id}, 角色: {role}")
    
    return render_template('account.html', username=username, last_login=last_login, role=role)

@main_bp.route('/session_check')
def session_check():
    """会话状态检查API，用于诊断会话问题"""
    # 检查会话状态
    is_logged_in = 'user' in session
    username = session.get('user', '未登录')
    session_id = session.sid if hasattr(session, 'sid') else '未知'
    
    # 记录会话检查日志
    logging.info(f"会话状态检查 - 用户: {username}, 已登录: {is_logged_in}, 会话ID: {session_id}")
    
    return jsonify({
        'logged_in': is_logged_in,
        'username': username,
        'session_id': session_id
    }) 