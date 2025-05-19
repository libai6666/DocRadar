"""
DocRadar - 本地文档搜索系统
主应用入口文件
"""
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_file, session, make_response
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
import mimetypes

from utils.document_parser import DocumentParser
from utils.search_engine import SearchEngine
from utils.storage import Storage
import config

# 日志目录和文件
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
# 按天分割日志文件
log_file = os.path.join(log_dir, f'docRadar_{datetime.now().strftime("%Y%m%d")}.log')

# 自动清理7天前的日志
for fname in os.listdir(log_dir):
    if fname.startswith('docRadar_') and fname.endswith('.log'):
        try:
            date_str = fname[len('docRadar_'):-len('.log')]
            log_date = datetime.strptime(date_str, '%Y%m%d')
            if (datetime.now() - log_date).days > 7:
                os.remove(os.path.join(log_dir, fname))
        except Exception as e:
            logging.warning(f'日志清理失败: {fname}, {e}')

# 配置日志到文件和控制台
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logging.getLogger().addHandler(file_handler)

# 初始化Flask应用
app = Flask(__name__)
app.config.from_object(config)

# 输出ADMIN_KEY到日志，方便管理员使用
logging.info(f"Current ADMIN_KEY: {app.config.get('ADMIN_KEY')}")

# 确保上传目录存在
if not os.path.exists(config.UPLOAD_FOLDER):
    os.makedirs(config.UPLOAD_FOLDER)

# 初始化存储、搜索引擎
storage = Storage()
search_engine = SearchEngine()

def add_security_headers(response):
    """添加安全相关的响应头"""
    # 构建 CSP 头
    csp_parts = []
    for directive, sources in config.CSP.items():
        csp_parts.append(f"{directive} {' '.join(sources)}")
    csp_header = "; ".join(csp_parts)
    
    # 添加安全头
    response.headers['Content-Security-Policy'] = csp_header
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response

# 注册安全头中间件
app.after_request(add_security_headers)

# 管理功能访问控制
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_key = request.args.get('key')
        if admin_key != app.config.get('ADMIN_KEY'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# 数据库管理辅助函数
def get_db_tables():
    """获取数据库所有表名"""
    import sqlite3
    conn = sqlite3.connect(config.DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def get_table_info(table_name):
    """获取表结构信息"""
    import sqlite3
    conn = sqlite3.connect(config.DATABASE)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    conn.close()
    return columns

def get_table_data(table_name, page=1, limit=50):
    """获取表数据（分页）"""
    import sqlite3
    offset = (page - 1) * limit
    conn = sqlite3.connect(config.DATABASE)
    
    # 检查表是否存在
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        conn.close()
        return {
            'columns': [],
            'data': [],
            'total': 0,
            'page': page,
            'limit': limit,
            'pages': 0,
            'has_id_column': False
        }
    
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns_info = cursor.fetchall()
    
    # 检查是否有ID列及其位置
    id_column_index = -1
    for i, col in enumerate(columns_info):
        if col[1].lower() == 'id' and col[2].lower() in ('integer', 'int'):
            id_column_index = i
            break
    
    # 获取数据
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset};")
    data = cursor.fetchall()
    
    # 获取总记录数
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    total = cursor.fetchone()[0]
    
    # 获取列名
    columns = [col[1] for col in columns_info]
    
    conn.close()
    
    return {
        'columns': columns,
        'data': data,
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit,
        'has_id_column': id_column_index >= 0,
        'id_column_index': id_column_index
    }

def execute_query(query, params=None):
    """执行自定义SQL查询"""
    import sqlite3
    conn = sqlite3.connect(config.DATABASE)
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
            # 获取列名
            columns = [description[0] for description in cursor.description]
            # 获取数据
            data = cursor.fetchall()
            conn.close()
            return {'success': True, 'columns': columns, 'data': data}
        else:
            # 非查询操作
            conn.commit()
            conn.close()
            return {'success': True, 'affected_rows': cursor.rowcount}
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}

@app.route('/')
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

@app.route('/api/documents')
def get_documents():
    """获取文档列表API"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('search', '')
    
    try:
        documents_data = storage.get_all_documents(page=page, limit=limit, search_query=search)
        return jsonify(documents_data)
    except Exception as e:
        logging.error(f"获取文档列表失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-file')
def check_existing_file():
    """检查文件是否已存在"""
    filename = request.args.get('filename', '')
    
    if not filename:
        return jsonify({
            'exists': False,
            'error': '文件名不能为空'
        })
    
    try:
        # 使用原始文件名检查
        result = storage.check_file_exists(filename)
        return jsonify(result)
    except Exception as e:
        logging.error(f"检查文件存在失败: {e}")
        return jsonify({
            'exists': False,
            'error': str(e)
        })

@app.route('/upload', methods=['POST'])
def upload_file():
    """文件上传处理"""
    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(request.url)
        
    file = request.files['file']
    
    if file.filename == '':
        flash('没有选择文件')
        return redirect(request.url)
        
    try:
        # 获取是否覆盖参数
        overwrite = request.form.get('overwrite', 'false') == 'true'
        
        result = process_upload(file, overwrite)
        if result['success']:
            flash('文件上传成功')
        else:
            flash(f'文件上传失败: {result["error"]}')
            
    except Exception as e:
        logging.error(f"文件上传失败: {e}")
        flash(f'文件上传失败: {str(e)}')
        
    return redirect(url_for('index'))

@app.route('/upload/batch', methods=['POST'])
def upload_batch():
    """批量文件上传处理（Ajax）"""
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': '没有选择文件'
        })
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': '文件名为空'
        })
    
    try:
        # 获取是否覆盖参数
        overwrite = request.form.get('overwrite', 'false') == 'true'
        
        # 处理单个文件上传（前端会逐个发送请求）
        result = process_upload(file, overwrite)
        
        # 检查是否存在但没有覆盖
        if not result['success'] and result.get('exists', False) and not overwrite:
            result['needs_confirmation'] = True
            
        return jsonify(result)
            
    except Exception as e:
        logging.error(f"批量上传失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

def process_upload(file, overwrite=False):
    """
    处理文件上传（供单个和批量上传使用）
    
    Args:
        file: 上传的文件对象
        overwrite: 是否覆盖已存在的文件
        
    Returns:
        dict: 处理结果
    """
    try:
        # 保存原始文件名
        original_filename = file.filename
        
        # 安全处理文件名
        filename = secure_filename(file.filename)
        file_type = storage.get_file_type(filename)
        
        logging.info(f"原始文件名: {original_filename}, 安全文件名: {filename}")
        
        # 检查文件类型是否支持
        ext = os.path.splitext(filename)[1].lower()[1:]
        if ext not in config.ALLOWED_EXTENSIONS:
            return {
                'success': False,
                'error': f'不支持的文件类型: {ext}'
            }
        
        # 检查文件是否已存在
        file_exists = storage.check_file_exists(original_filename)
        if file_exists['exists'] and not overwrite:
            return {
                'success': False,
                'error': f'文件 "{original_filename}" 已存在',
                'exists': True,
                'filename': original_filename,
                'existing_doc': file_exists
            }
        
        # 如果文件存在且允许覆盖，先删除旧文件
        if file_exists['exists'] and overwrite:
            # 确保file_exists有id字段
            if 'id' not in file_exists and 'doc_id' in file_exists:
                file_exists['id'] = file_exists['doc_id']
                
            storage.delete_document(file_exists['id'])
            logging.info(f"覆盖旧文件: {file_exists['id']}")
        
        # 保存文件
        file_path = storage.save_file(file, filename)
        
        # 解析文档内容
        parser = DocumentParser.get_parser(file_path)
        
        # 添加文档元数据（先添加以获取文档ID）
        title = os.path.splitext(original_filename)[0]  # 默认使用文件名作为标题
        file_size = os.path.getsize(file_path)
        
        # 添加文档元数据
        doc_id = storage.add_document_metadata(
            filename=original_filename,
            filepath=file_path,
            title=title,
            file_type=file_type,
            file_size=file_size,
            metadata=None,
            original_filename=original_filename
        )
        
        # 解析文档内容（传递文档ID）
        doc_content = parser.parse(file_path, doc_id)
        
        # 更新文档元数据
        title = doc_content['metadata'].get('title', filename)
        storage.update_document_metadata(
            doc_id,
            title=title,
            metadata=doc_content['metadata']
        )
        
        # 添加文档内容到索引
        storage.add_document_content(
            doc_id,
            doc_content['text'],
            doc_content.get('html_content', '')
        )
        
        # 更新搜索索引
        search_engine.index_document(
            doc_id,
            title,
            doc_content['text'],
            file_type
        )
        
        return {
            'success': True,
            'doc_id': doc_id,
            'filename': filename,
            'overwritten': file_exists['exists'] and overwrite
        }
        
    except Exception as e:
        logging.error(f"文件处理失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/search')
def search():
    """搜索处理"""
    query = request.args.get('q', '')
    
    if not query:
        return render_template('results.html', query='', results=[], search_history=[])
    
    try:
        # 执行搜索（现在使用基于LIKE的搜索）
        results = search_engine.search(query)
        
        # 为当前结果添加doc_url
        for result in results:
            result['doc_url'] = url_for('view_document', doc_id=result['id'], q=query)
        
        # 获取或初始化搜索历史
        if 'search_history' not in session:
            session['search_history'] = []
        
        # 添加新的搜索记录
        search_history = session['search_history']
        
        # 克隆结果列表，添加到历史
        history_results = []
        for result in results:
            # 复制结果字典，以确保修改历史不会影响当前视图
            history_result = result.copy()
            # 确保历史记录中保存的结果也有doc_url
            history_result['doc_url'] = url_for('view_document', doc_id=result['id'], q=query)
            history_results.append(history_result)
        
        # 检查是否已存在相同关键词的搜索记录
        existing_record = None
        for record in search_history:
            if record['query'] == query:
                existing_record = record
                break
        
        if existing_record:
            # 更新已存在的记录
            existing_record['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            existing_record['results'] = history_results
            # 不改变ID，只更新内容和时间戳
        else:
            # 分配一个唯一ID（避免ID冲突）
            max_id = 0
            for record in search_history:
                if record.get('id', 0) > max_id:
                    max_id = record['id']
            
            # 添加新记录
            search_history.append({
                'id': max_id + 1,
                'query': query,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'results': history_results
            })
        
        # 限制历史记录数量（保留最近10次）
        if len(search_history) > 10:
            # 按ID排序，保留ID最大的10条记录
            search_history.sort(key=lambda x: x.get('id', 0))
            search_history = search_history[-10:]
        
        session['search_history'] = search_history
        
        return render_template(
            'results.html',
            query=query,
            results=results,
            search_history=search_history
        )
    except Exception as e:
        logging.error(f"搜索失败: {e}")
        flash(f'搜索失败: {str(e)}')
        return render_template('results.html', query=query, results=[], search_history=[])

@app.route('/document/<int:doc_id>')
def view_document(doc_id):
    """查看文档内容"""
    query = request.args.get('q', '')
    
    try:
        document = search_engine.get_document_by_id(doc_id)
        
        if not document:
            flash('找不到该文档，可能已被删除。')
            return redirect(url_for('index'))
        
        # 记录调试信息
        logging.info(f"查看文档: {doc_id}, 文件类型: {document['file_type']}")
        
        # 检查content是否存在且不为空
        if 'content' not in document or not document['content']:
            logging.warning(f"文档 {doc_id} 内容为空")
            # 设置一个友好的提示消息作为内容
            document['content'] = "无法加载文档内容。可能是因为索引系统不可用或文件已损坏。"
            flash('文档内容加载失败，只显示基本信息。')
        
        # 优先使用HTML内容，如果有的话
        if 'html_content' in document:
            logging.info(f"文档 {doc_id} 使用HTML内容显示")
            document['content'] = document['html_content']
        # 如果有搜索查询且内容不是错误消息，高亮显示匹配内容
        elif query and not document['content'].startswith("无法加载"):
            try:
                # 使用增强的高亮方法
                document['content'] = search_engine.highlight_content(document['content'], query)
                logging.info(f"已高亮文档内容中的搜索词 '{query}'")
            except Exception as highlight_error:
                logging.error(f"高亮处理失败: {highlight_error}")
                # 高亮失败不影响内容显示
            
        return render_template('view.html', document=document, query=query)
    except Exception as e:
        logging.error(f"查看文档失败: {e}")
        flash(f'查看文档失败: {str(e)}')
        return redirect(url_for('index'))

@app.route('/document/<int:doc_id>/original')
def download_original(doc_id):
    """下载原始文档"""
    try:
        conn = storage.db_path
        import sqlite3
        conn = sqlite3.connect(conn)
        cursor = conn.cursor()
        
        cursor.execute("SELECT filepath, filename, original_filename FROM documents WHERE id = ?", (doc_id,))
        result = cursor.fetchone()
        
        if not result:
            abort(404)
            
        filepath, filename, original_filename = result
        download_name = original_filename if original_filename else filename
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        logging.error(f"下载文档失败: {e}")
        flash(f'下载文档失败: {str(e)}')
        return redirect(url_for('index'))

@app.route('/document/<int:doc_id>/delete', methods=['POST'])
def delete_document(doc_id):
    """删除文档"""
    try:
        success = storage.delete_document(doc_id)
        
        if success:
            flash('文档删除成功')
        else:
            flash('文档删除失败')
            
    except Exception as e:
        logging.error(f"删除文档失败: {e}")
        flash(f'删除文档失败: {str(e)}')
        
    return redirect(url_for('index'))

@app.route('/api/search')
def api_search():
    """搜索API，用于异步搜索请求"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'results': []})
        
    try:
        # 使用基于LIKE的搜索
        results = search_engine.search(query)
        return jsonify({'results': results})
    except Exception as e:
        logging.error(f"API搜索失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/search/delete/<int:history_id>')
def delete_search_history(history_id):
    """删除搜索历史记录"""
    # 保存当前请求的引用页面或查询参数
    referer = request.referrer
    current_query = request.args.get('q', '')
    success = False
    
    if 'search_history' in session:
        search_history = session['search_history']
        # 找到并删除指定ID的搜索记录
        updated_history = [h for h in search_history if h['id'] != history_id]
        
        # 检查是否真的删除了记录
        if len(updated_history) < len(search_history):
            session['search_history'] = updated_history
            success = True
            flash('搜索记录已删除')
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        # 如果是AJAX请求，返回JSON响应
        return jsonify({
            'success': success,
            'history_id': history_id,
            'message': '搜索记录已删除' if success else '删除失败'
        })
    
    # 对于常规请求，重定向回搜索页面
    # 优先使用当前查询参数，如果没有则尝试从引用页提取查询参数
    if current_query:
        return redirect(url_for('search', q=current_query))
    elif referer and 'search?q=' in referer:
        # 从引用URL中提取查询参数
        try:
            query_part = referer.split('search?q=')[1].split('&')[0]
            if query_part:
                return redirect(url_for('search', q=query_part))
        except:
            pass
    
    # 如果没有可用查询，返回到搜索页
    return redirect(url_for('search', q=''))

@app.route('/search/clear')
def clear_search_history():
    """清空所有搜索历史记录"""
    # 保存当前请求的引用页面或查询参数
    referer = request.referrer
    current_query = request.args.get('q', '')
    
    # 检查session中是否有搜索历史
    if 'search_history' in session:
        # 替换为空列表，确保完全清空
        session['search_history'] = []
        # 强制session更新
        session.modified = True
        # 确保session变更被保存
        session.permanent = True
        logging.info("搜索历史记录已清空")
        flash('所有搜索记录已清空')
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        # 如果是AJAX请求，返回JSON响应
        return jsonify({
            'success': True,
            'message': '所有搜索记录已清空'
        })
    
    # 优先使用当前查询参数，如果没有则尝试从引用页提取查询参数
    if current_query:
        return redirect(url_for('search', q=current_query))
    elif referer and 'search?q=' in referer:
        # 从引用URL中提取查询参数
        try:
            query_part = referer.split('search?q=')[1].split('&')[0]
            if query_part:
                return redirect(url_for('search', q=query_part))
        except:
            pass
    
    return redirect(url_for('search', q=''))

# 数据库管理路由
@app.route('/admin/db')
@admin_required
def db_admin():
    """数据库管理界面"""
    tables = get_db_tables()
    return render_template('admin/db.html', tables=tables, config=config)

@app.route('/admin/db/table/<table_name>')
@admin_required
def view_table(table_name):
    """查看表数据"""
    try:
        page = request.args.get('page', 1, type=int)
        table_info = get_table_info(table_name)
        table_data = get_table_data(table_name, page=page)
        
        # 特殊表的处理标志
        special_tables = ['sqlite_sequence', 'document_content_config', 
                          'document_content', 'document_content_data', 
                          'document_content_idx', 'document_content_content', 
                          'document_content_docsize']
        
        is_special_table = table_name in special_tables
        
        return render_template(
            'admin/table.html', 
            table_name=table_name,
            table_info=table_info,
            table_data=table_data,
            is_special_table=is_special_table
        )
    except Exception as e:
        logging.error(f"查看表数据出错: {str(e)}")
        flash(f'查看表数据出错: {str(e)}')
        return redirect(url_for('db_admin', key=request.args.get('key')))

@app.route('/admin/db/query', methods=['GET', 'POST'])
@admin_required
def db_query():
    """执行SQL查询"""
    result = None
    query = ''
    
    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            # 允许执行任何SQL查询
            result = execute_query(query)
    
    return render_template('admin/query.html', query=query, result=result)

@app.route('/admin/db/export/<table_name>')
@admin_required
def export_table(table_name):
    """导出表数据为CSV"""
    import sqlite3
    conn = sqlite3.connect(config.DATABASE)
    cursor = conn.cursor()
    
    # 获取列名
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [col[1] for col in cursor.fetchall()]
    
    # 获取数据
    cursor.execute(f"SELECT * FROM {table_name};")
    data = cursor.fetchall()
    conn.close()
    
    # 创建CSV内容
    csv_data = [','.join(columns)]
    for row in data:
        csv_data.append(','.join([str(cell) if cell is not None else '' for cell in row]))
    
    # 创建响应
    response = make_response('\n'.join(csv_data))
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={table_name}.csv'
    
    return response

@app.route('/admin/db/edit/<table_name>/<int:record_id>', methods=['GET', 'POST'])
@admin_required
def edit_record(table_name, record_id):
    """编辑记录"""
    try:
        # 检查表是否为特殊表
        special_tables = ['sqlite_sequence', 'document_content_config', 
                         'document_content', 'document_content_data', 
                         'document_content_idx', 'document_content_content', 
                         'document_content_docsize']
        
        if table_name in special_tables:
            flash('不能编辑系统特殊表')
            return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
            
        if request.method == 'POST':
            # 获取表结构
            columns = [col[1] for col in get_table_info(table_name) if col[1].lower() != 'id']
            
            if not columns:
                flash('表结构获取失败或表没有可编辑的列')
                return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
            
            # 构建更新语句
            sets = []
            values = []
            for col in columns:
                value = request.form.get(col, '')
                sets.append(f"{col} = ?")
                values.append(value if value else None)
            
            # 添加ID作为条件
            values.append(record_id)
            
            # 执行更新
            query = f"UPDATE {table_name} SET {', '.join(sets)} WHERE id = ?"
            result = execute_query(query, values)
            
            if result['success']:
                flash('记录更新成功')
            else:
                flash(f'记录更新失败: {result["error"]}')
            
            # 重定向回表格视图
            return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
        
        # GET请求，获取记录详情
        query = f"SELECT * FROM {table_name} WHERE id = ?"
        result = execute_query(query, (record_id,))
        
        if not result['success'] or not result['data']:
            flash('未找到记录')
            return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
        
        record = dict(zip(result['columns'], result['data'][0]))
        columns = get_table_info(table_name)
        
        return render_template(
            'admin/edit_record.html', 
            table_name=table_name,
            record=record,
            columns=columns
        )
    except Exception as e:
        logging.error(f"编辑记录出错: {str(e)}")
        flash(f'编辑记录出错: {str(e)}')
        return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))

@app.route('/admin/db/delete/<table_name>/<int:record_id>', methods=['POST'])
@admin_required
def delete_record(table_name, record_id):
    """删除记录"""
    try:
        # 检查表是否为特殊表
        special_tables = ['sqlite_sequence', 'document_content_config', 
                         'document_content', 'document_content_data', 
                         'document_content_idx', 'document_content_content', 
                         'document_content_docsize']
        
        if table_name in special_tables:
            flash('不能删除系统特殊表的记录')
            return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
            
        query = f"DELETE FROM {table_name} WHERE id = ?"
        result = execute_query(query, (record_id,))
        
        if result['success']:
            flash('记录删除成功')
        else:
            flash(f'记录删除失败: {result["error"]}')
        
        return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
    except Exception as e:
        logging.error(f"删除记录出错: {str(e)}")
        flash(f'删除记录出错: {str(e)}')
        return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))

@app.route('/admin/db/add/<table_name>', methods=['GET', 'POST'])
@admin_required
def add_record(table_name):
    """添加记录"""
    try:
        # 检查表是否为特殊表
        special_tables = ['sqlite_sequence', 'document_content_config', 
                         'document_content', 'document_content_data', 
                         'document_content_idx', 'document_content_content', 
                         'document_content_docsize']
        
        if table_name in special_tables:
            flash('不能向系统特殊表添加记录')
            return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
            
        # 检查表结构
        table_info = get_table_info(table_name)
        table_data = get_table_data(table_name, page=1)
        
        if not table_data['has_id_column']:
            flash('该表没有ID列，无法添加记录')
            return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
            
        if request.method == 'POST':
            # 获取表结构
            columns = [col[1] for col in table_info if col[1].lower() != 'id']
            
            if not columns:
                flash('表结构获取失败或表没有可添加的列')
                return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
            
            # 构建插入语句
            values = []
            for col in columns:
                value = request.form.get(col, '')
                values.append(value if value else None)
            
            placeholders = ', '.join(['?' for _ in columns])
            columns_str = ', '.join(columns)
            
            # 执行插入
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            result = execute_query(query, values)
            
            if result['success']:
                flash('记录添加成功')
            else:
                flash(f'记录添加失败: {result["error"]}')
            
            # 重定向回表格视图
            return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))
        
        # GET请求，显示添加表单
        return render_template(
            'admin/add_record.html', 
            table_name=table_name,
            columns=table_info
        )
    except Exception as e:
        logging.error(f"添加记录出错: {str(e)}")
        flash(f'添加记录出错: {str(e)}')
        return redirect(url_for('view_table', table_name=table_name, key=request.args.get('key')))

@app.route('/documents/batch-delete', methods=['POST'])
def batch_delete_documents():
    """批量删除文档"""
    try:
        # 获取要删除的文档ID列表
        doc_ids = request.json.get('doc_ids', [])
        
        if not doc_ids:
            return jsonify({
                'success': False,
                'message': '未提供要删除的文档ID'
            })
        
        # 记录删除请求
        logging.info(f"批量删除文档请求: {doc_ids}")
        
        # 存储删除结果
        results = {
            'success': [],
            'failed': []
        }
        
        # 逐个删除文档
        for doc_id in doc_ids:
            try:
                success = storage.delete_document(doc_id)
                if success:
                    results['success'].append(doc_id)
                else:
                    results['failed'].append(doc_id)
            except Exception as e:
                logging.error(f"删除文档 {doc_id} 失败: {e}")
                results['failed'].append(doc_id)
        
        # 返回结果
        message = f"成功删除 {len(results['success'])} 个文档"
        if results['failed']:
            message += f"，{len(results['failed'])} 个文档删除失败"
        
        return jsonify({
            'success': True,
            'message': message,
            'results': results
        })
            
    except Exception as e:
        logging.error(f"批量删除文档失败: {e}")
        return jsonify({
            'success': False,
            'message': f'批量删除文档失败: {str(e)}'
        })

@app.errorhandler(403)
def forbidden(e):
    """403错误处理"""
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    """404错误处理"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """500错误处理"""
    return render_template('500.html'), 500

@app.route('/static/doc_images/<path:filename>')
def serve_doc_image(filename):
    """提供文档图片文件"""
    try:
        # 获取图片文件的完整路径
        image_path = os.path.join(app.static_folder, 'doc_images', filename)
        logging.info(f"请求图片: {filename}")
        logging.info(f"图片完整路径: {image_path}")
        
        if not os.path.exists(image_path):
            logging.warning(f"请求的图片不存在: {image_path}")
            abort(404)
            
        # 设置正确的MIME类型
        mime_type = mimetypes.guess_type(image_path)[0] or 'application/octet-stream'
        logging.info(f"图片MIME类型: {mime_type}")
        
        return send_file(
            image_path,
            mimetype=mime_type,
            cache_timeout=3600  # 缓存1小时
        )
    except Exception as e:
        logging.error(f"提供文档图片失败: {e}")
        abort(404)

if __name__ == '__main__':
    app.run(debug=True) 