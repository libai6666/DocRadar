"""
DocRadar - 文档管理路由
处理文档上传、查看、删除等操作
"""
import os
import logging
from flask import Blueprint, request, redirect, url_for, flash, jsonify, send_file, abort
from flask import session, render_template
from werkzeug.utils import secure_filename

from app.core.auth import login_required
from app.utils.document_parser import DocumentParser
from app.utils.search_engine import SearchEngine
from app.utils.storage import Storage
from app.core.config import ALLOWED_EXTENSIONS

# 创建蓝图
document_bp = Blueprint('document', __name__, url_prefix='/document')

# 初始化存储、搜索引擎
storage = Storage()
search_engine = SearchEngine()

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
        if ext not in ALLOWED_EXTENSIONS:
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
        title = os.path.splitext(original_filename)[0]
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
        title = doc_content['metadata'].get('title', title)
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

@document_bp.route('/<int:doc_id>')
@login_required
def view_document(doc_id):
    """查看文档内容"""
    query = request.args.get('q', '')
    
    try:
        document = search_engine.get_document_by_id(doc_id)
        
        if not document:
            flash('找不到该文档，可能已被删除。')
            return redirect(url_for('main.index'))
        
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
        
        # 不再在后端进行高亮处理，交由前端处理
        # 记录查询参数，用于前端搜索
        logging.info(f"传递查询参数到模板: '{query}'")
            
        return render_template('view.html', document=document, query=query)
    except Exception as e:
        logging.error(f"查看文档失败: {e}")
        flash(f'查看文档失败: {str(e)}')
        return redirect(url_for('main.index'))

@document_bp.route('/<int:doc_id>/original')
@login_required
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
        return redirect(url_for('main.index'))

@document_bp.route('/<int:doc_id>/delete', methods=['POST'])
@login_required
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
        
    return redirect(url_for('main.index'))

@document_bp.route('/batch-delete', methods=['POST'])
@login_required
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

@document_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """单个文档上传处理"""
    # 检查请求中是否有文件
    if 'file' not in request.files:
        flash('没有提供文件')
        return redirect(request.referrer or url_for('main.index'))
    
    file = request.files['file']
    
    # 检查文件名是否为空
    if file.filename == '':
        flash('未选择文件')
        return redirect(request.referrer or url_for('main.index'))
    
    # 检查覆盖选项
    overwrite = request.form.get('overwrite', 'false') == 'true'
    
    # 处理文件上传
    result = process_upload(file, overwrite)
    
    if result['success']:
        flash(f'文件 "{file.filename}" 上传成功')
        if result.get('overwritten'):
            flash('已覆盖同名文件')
    else:
        if result.get('exists'):
            flash(f'文件 "{file.filename}" 已存在。如需覆盖，请勾选"覆盖已有文件"选项。')
        else:
            flash(f'文件上传失败: {result.get("error", "未知错误")}')
    
    return redirect(url_for('main.index'))

@document_bp.route('/upload/batch', methods=['POST'])
@login_required
def batch_upload_documents():
    """批量文档上传处理"""
    # 检查请求中是否有文件
    if 'files[]' not in request.files:
        return jsonify({
            'success': False,
            'message': '没有提供文件'
        })
    
    files = request.files.getlist('files[]')
    
    # 检查是否有文件
    if not files or all(file.filename == '' for file in files):
        return jsonify({
            'success': False,
            'message': '未选择文件'
        })
    
    # 检查覆盖选项
    overwrite = request.form.get('overwrite', 'false') == 'true'
    
    # 处理每个文件
    results = []
    
    for file in files:
        if file.filename != '':
            # 处理单个文件
            result = process_upload(file, overwrite)
            result['filename'] = file.filename
            results.append(result)
    
    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count
    
    return jsonify({
        'success': True,
        'message': f'上传完成: {success_count} 个成功, {fail_count} 个失败',
        'results': results
    })

@document_bp.route('/api/check-file', methods=['POST'])
@login_required
def check_file_exists():
    """检查文件是否已存在"""
    filename = request.json.get('filename', '')
    
    if not filename:
        return jsonify({
            'success': False,
            'message': '未提供文件名'
        })
    
    result = storage.check_file_exists(filename)
    
    return jsonify({
        'success': True,
        'exists': result.get('exists', False),
        'file_info': result
    }) 