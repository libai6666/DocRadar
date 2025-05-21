"""
DocRadar - 管理功能路由
处理数据库管理、用户管理等管理功能
"""
import os
import json
import logging
import sqlite3
import csv
from io import StringIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, send_file
from flask import session, make_response
from datetime import datetime

from app.core.auth import admin_required, login_required, add_user, delete_user, get_users, get_user_role
from app.core.config import DATABASE_URI, ADMIN_KEY

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def check_admin_key(key):
    """验证管理员密钥"""
    return key == ADMIN_KEY

@admin_bp.route('/db')
def db_management():
    """数据库管理页面"""
    key = request.args.get('key', '')
    
    if not check_admin_key(key):
        abort(403)
    
    # 获取数据库所有表
    try:
        conn = sqlite3.connect(DATABASE_URI)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('admin/db_management.html', tables=tables, key=key)
    except Exception as e:
        logging.error(f"获取数据库表失败: {e}")
        return render_template('admin/db_management.html', tables=[], key=key, error=str(e))

@admin_bp.route('/db/table/<table_name>')
def view_table(table_name):
    """查看表内容"""
    key = request.args.get('key', '')
    
    if not check_admin_key(key):
        abort(403)
    
    try:
        conn = sqlite3.connect(DATABASE_URI)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [dict(row) for row in cursor.fetchall()]
        
        # 获取表数据
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
        rows = [dict(row) for row in cursor.fetchall()]
        
        # 获取表总记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return render_template(
            'admin/view_table.html', 
            table_name=table_name, 
            columns=columns, 
            rows=rows, 
            key=key,
            limit=limit,
            offset=offset,
            total_count=total_count
        )
    except Exception as e:
        logging.error(f"查看表失败: {e}")
        return render_template(
            'admin/view_table.html', 
            table_name=table_name, 
            columns=[], 
            rows=[], 
            key=key, 
            error=str(e)
        )

@admin_bp.route('/db/query', methods=['GET', 'POST'])
def execute_query():
    """执行SQL查询"""
    key = request.args.get('key', '')
    
    if not check_admin_key(key):
        abort(403)
    
    if request.method == 'POST':
        sql = request.form.get('sql', '')
        result_type = request.form.get('result_type', 'table')
        
        if not sql:
            return render_template('admin/query.html', key=key, error='请输入SQL查询')
        
        try:
            conn = sqlite3.connect(DATABASE_URI)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 执行查询
            cursor.execute(sql)
            
            if sql.strip().upper().startswith(('SELECT', 'PRAGMA', 'EXPLAIN')):
                # 查询操作，返回结果
                results = cursor.fetchall()
                
                if result_type == 'json':
                    # 返回JSON结果
                    # 将Row对象转换为dict
                    json_results = [dict(row) for row in results]
                    return jsonify({
                        'success': True,
                        'results': json_results,
                        'count': len(json_results)
                    })
                else:
                    # 返回表格结果
                    if results:
                        columns = list(results[0].keys())
                        rows = [dict(row) for row in results]
                    else:
                        columns = []
                        rows = []
                        
                    return render_template(
                        'admin/query.html',
                        key=key,
                        sql=sql,
                        columns=columns,
                        rows=rows,
                        row_count=len(rows),
                        result_type=result_type
                    )
            else:
                # 更新操作，返回影响的行数
                conn.commit()
                rowcount = cursor.rowcount
                
                if result_type == 'json':
                    # 返回JSON结果
                    return jsonify({
                        'success': True,
                        'message': f'操作成功，影响了 {rowcount} 行',
                        'rowcount': rowcount
                    })
                else:
                    # 返回消息
                    return render_template(
                        'admin/query.html',
                        key=key,
                        sql=sql,
                        message=f'操作成功，影响了 {rowcount} 行',
                        result_type=result_type
                    )
                
        except Exception as e:
            logging.error(f"执行SQL查询失败: {e}")
            
            if result_type == 'json':
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
            else:
                return render_template('admin/query.html', key=key, sql=sql, error=str(e), result_type=result_type)
        finally:
            if conn:
                conn.close()
    
    # GET请求，返回查询页面
    return render_template('admin/query.html', key=key)

@admin_bp.route('/db/export/<table_name>')
def export_table(table_name):
    """导出表为CSV"""
    key = request.args.get('key', '')
    
    if not check_admin_key(key):
        abort(403)
    
    try:
        conn = sqlite3.connect(DATABASE_URI)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取表所有记录
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            return "表中没有数据"
            
        # 获取列名
        columns = list(rows[0].keys())
        
        # 创建CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(columns)
        
        # 写入数据
        for row in rows:
            writer.writerow([row[column] for column in columns])
        
        # 创建响应
        response = make_response(output.getvalue())
        
        # 设置文件名和MIME类型
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response.headers['Content-Disposition'] = f'attachment; filename={table_name}_{timestamp}.csv'
        response.headers['Content-Type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        logging.error(f"导出表失败: {e}")
        return str(e)
    finally:
        if conn:
            conn.close()

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """用户管理页面"""
    users = get_users()
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_new_user():
    """添加新用户"""
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'user')
    
    if not username or not password:
        flash('用户名和密码不能为空', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    if len(password) < 8:
        flash('密码长度必须至少为8个字符', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    # 添加用户
    success = add_user(username, password, role)
    
    if success:
        flash(f'用户 {username} 添加成功', 'success')
    else:
        flash(f'用户 {username} 已存在', 'danger')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/delete/<username>', methods=['POST'])
@login_required
@admin_required
def remove_user(username):
    """删除用户"""
    # 不允许删除当前登录用户
    if username == session.get('user'):
        flash('不能删除当前登录的用户', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    # 不允许删除唯一的管理员
    users = get_users()
    admin_count = sum(1 for user in users if users[user].get('role') == 'admin')
    
    if admin_count <= 1 and get_user_role(username) == 'admin':
        flash('不能删除唯一的管理员', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    # 删除用户
    success = delete_user(username)
    
    if success:
        flash(f'用户 {username} 删除成功', 'success')
    else:
        flash(f'用户 {username} 不存在', 'danger')
    
    return redirect(url_for('admin.manage_users')) 