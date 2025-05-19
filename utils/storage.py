"""
存储管理模块
处理文件存储和元数据管理
"""
import os
import sqlite3
import json
import logging
import shutil
import uuid
from werkzeug.utils import secure_filename
from config import DATABASE, UPLOAD_FOLDER, ALLOWED_EXTENSIONS

class Storage:
    """存储管理类，负责文件存储和元数据管理"""
    
    def __init__(self, db_path=DATABASE, upload_folder=UPLOAD_FOLDER):
        """
        初始化存储管理
        
        Args:
            db_path: 数据库文件路径
            upload_folder: 上传文件存储目录
        """
        self.db_path = db_path
        self.upload_folder = upload_folder
        
        # 确保上传目录存在
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
    
    def save_file(self, file, filename=None):
        """
        保存上传的文件
        
        Args:
            file: 文件对象
            filename: 可选的文件名
            
        Returns:
            str: 保存的文件路径
        """
        if filename is None:
            filename = secure_filename(file.filename)
        
        # 获取文件扩展名
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        # 检查文件类型是否支持
        if ext[1:] not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # 使用UUID创建唯一文件名，避免冲突
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(self.upload_folder, unique_filename)
        
        # 保存文件
        file.save(file_path)
        logging.info(f"File saved: {file_path}")
        
        return file_path
    
    def add_document_metadata(self, filename, filepath, title, file_type, file_size, metadata=None, original_filename=None):
        """
        添加文档元数据到数据库
        
        Args:
            filename: 存储的文件名（基本文件名）
            filepath: 存储的文件路径
            title: 文档标题
            file_type: 文件类型
            file_size: 文件大小
            metadata: 文档元数据字典
            original_filename: 原始文件名（包含前缀等）
            
        Returns:
            int: 文档ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 如果没有提供原始文件名，使用基本文件名
            if original_filename is None:
                original_filename = filename
            
            # 序列化元数据为JSON
            metadata_json = json.dumps(metadata) if metadata else None
            
            # 插入元数据
            cursor.execute('''
            INSERT INTO documents 
                (filename, filepath, title, file_type, file_size, metadata, original_filename)
            VALUES 
                (?, ?, ?, ?, ?, ?, ?)
            ''', (filename, filepath, title, file_type, file_size, metadata_json, original_filename))
            
            doc_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logging.info(f"Document metadata added with ID: {doc_id}, filename: {filename}, original_filename: {original_filename}")
            return doc_id
            
        except sqlite3.Error as e:
            logging.error(f"Error adding document metadata: {e}")
            raise
    
    def delete_document(self, doc_id):
        """
        删除文档及其元数据
        
        Args:
            doc_id: 文档ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取文件路径和元数据
            cursor.execute("SELECT filepath, metadata, filename, original_filename FROM documents WHERE id = ?", (doc_id,))
            result = cursor.fetchone()
            
            if not result:
                logging.warning(f"Document not found: {doc_id}")
                conn.close()
                return False
                
            filepath = result['filepath']
            filename = result['filename']
            
            # 正确处理original_filename字段
            # 检查original_filename是否在结果中，并且不为None
            original_filename = filename  # 默认值
            if 'original_filename' in result.keys() and result['original_filename'] is not None:
                original_filename = result['original_filename']
            
            logging.info(f"开始删除文档 ID: {doc_id}, 文件名: {filename}, 原始文件名: {original_filename}")
            logging.info(f"文件路径: {filepath}")
            
            # 清理文档相关的所有文件
            try:
                # 1. 清理文档文件
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logging.info(f"删除文件: {filepath}")
                else:
                    logging.warning(f"文件不存在: {filepath}")
                    
                    # 如果filepath不是绝对路径，尝试构建绝对路径
                    if not os.path.isabs(filepath):
                        abs_filepath = os.path.join(self.upload_folder, os.path.basename(filepath))
                        if os.path.exists(abs_filepath):
                            os.remove(abs_filepath)
                            logging.info(f"删除文件(绝对路径): {abs_filepath}")
                
                # 2. 检查元数据中的图片目录
                if result['metadata']:
                    metadata = json.loads(result['metadata'])
                    # 清理文档关联的图片目录
                    if metadata and 'image_directory' in metadata:
                        image_dir = metadata['image_directory']
                        if os.path.exists(image_dir) and os.path.isdir(image_dir):
                            shutil.rmtree(image_dir)
                            logging.info(f"删除元数据中的图片目录: {image_dir}")
                
                # 3. 获取应用根目录和静态目录
                base_dir = os.path.dirname(os.path.dirname(__file__))
                static_dir = os.path.join(base_dir, 'static')
                doc_images_dir = os.path.join(static_dir, 'doc_images')
                
                # 4. 清理基于各种ID和文件名的图片目录
                patterns_to_check = [
                    # 基于文档ID
                    str(doc_id),
                    
                    # 基于文件路径
                    os.path.splitext(os.path.basename(filepath))[0],
                    
                    # 基于文件名
                    os.path.splitext(filename)[0],
                    
                    # 基于原始文件名
                    os.path.splitext(original_filename)[0] if original_filename else None,
                    
                    # 基于UUID (如果文件名是UUID格式)
                    os.path.basename(filepath)
                ]
                
                # 过滤掉None值
                patterns_to_check = [p for p in patterns_to_check if p]
                
                # 检查并清理匹配的目录
                for pattern in patterns_to_check:
                    pattern_dir = os.path.join(doc_images_dir, pattern)
                    if os.path.exists(pattern_dir) and os.path.isdir(pattern_dir):
                        shutil.rmtree(pattern_dir)
                        logging.info(f"删除图片目录: {pattern_dir}")
                
                # 5. 尝试查找可能的图片目录（模糊匹配）
                if os.path.exists(doc_images_dir) and os.path.isdir(doc_images_dir):
                    # 获取所有图片目录
                    for dirname in os.listdir(doc_images_dir):
                        dir_path = os.path.join(doc_images_dir, dirname)
                        if os.path.isdir(dir_path):
                            # 检查目录名是否与文件名相关
                            basename = os.path.splitext(filename)[0]
                            original_basename = os.path.splitext(original_filename)[0] if original_filename else None
                            
                            # 如果目录名包含文件名或原始文件名的一部分（至少5个字符），则删除
                            if ((basename and len(basename) >= 5 and basename in dirname) or
                                (original_basename and len(original_basename) >= 5 and original_basename in dirname)):
                                shutil.rmtree(dir_path)
                                logging.info(f"删除相关图片目录(模糊匹配): {dir_path}")
                
            except Exception as e:
                logging.error(f"清理文件时出错: {e}")
                # 继续处理文档删除，不因文件清理失败而中断
            
            # 删除文件记录
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            cursor.execute("DELETE FROM document_content WHERE doc_id = ?", (doc_id,))
            
            conn.commit()
            conn.close()
            
            logging.info(f"文档删除成功: {doc_id}")
            return True
            
        except (sqlite3.Error, OSError) as e:
            logging.error(f"删除文档失败: {e}")
            return False
    
    def get_documents_count(self, search_query=None):
        """
        获取文档总数
        
        Args:
            search_query: 可选的搜索查询条件
            
        Returns:
            int: 文档总数
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if search_query:
                # 如果有搜索查询，计算匹配的文档数
                cursor.execute('''
                SELECT COUNT(*) 
                FROM documents 
                WHERE title LIKE ? OR filename LIKE ?
                ''', (f'%{search_query}%', f'%{search_query}%'))
            else:
                # 否则计算所有文档数
                cursor.execute('SELECT COUNT(*) FROM documents')
                
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except sqlite3.Error as e:
            logging.error(f"Error counting documents: {e}")
            raise
    
    def get_all_documents(self, page=1, limit=None, search_query=None):
        """
        获取文档的元数据，支持分页和搜索
        
        Args:
            page: 页码（从1开始）
            limit: 每页数量，None表示获取所有
            search_query: 搜索关键字
            
        Returns:
            dict: 包含文档列表和分页信息
        """
        documents = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建SQL查询
            sql = '''
            SELECT 
                id, filename, filepath, title, file_type, file_size, created_at, original_filename 
            FROM 
                documents 
            '''
            
            params = []
            
            # 添加搜索条件
            if search_query:
                sql += "WHERE title LIKE ? OR filename LIKE ? OR original_filename LIKE ? "
                params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
            
            # 添加排序
            sql += "ORDER BY created_at DESC "
            
            # 添加分页
            if limit is not None:
                offset = (page - 1) * limit
                sql += "LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(sql, params)
            
            for row in cursor.fetchall():
                document = {
                    'id': row['id'],
                    'filename': row['filename'],
                    'filepath': row['filepath'],
                    'title': row['title'] or row['filename'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size'],
                    'created_at': row['created_at'],
                    'original_filename': row['original_filename'] if 'original_filename' in row.keys() else row['filename']
                }
                documents.append(document)
                
            conn.close()
            
            # 如果需要分页，返回额外的分页信息
            if limit is not None:
                total = self.get_documents_count(search_query)
                total_pages = (total + limit - 1) // limit if limit > 0 else 1
                
                return {
                    'documents': documents,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'total_pages': total_pages
                    }
                }
            
            # 否则只返回文档列表
            return documents
            
        except sqlite3.Error as e:
            logging.error(f"Error retrieving documents: {e}")
            raise
            
    def check_file_exists(self, filename):
        """
        检查文件名是否已存在于系统中
        
        Args:
            filename: 文件名
            
        Returns:
            dict: 包含是否存在及文档信息
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 先检查filename字段（基本文件名）
            cursor.execute('''
            SELECT id, filename, original_filename, title, file_type, file_size 
            FROM documents 
            WHERE filename = ?
            ''', (filename,))
            
            row = cursor.fetchone()
            
            # 如果没找到，再检查original_filename字段
            if not row:
                cursor.execute('''
                SELECT id, filename, original_filename, title, file_type, file_size 
                FROM documents 
                WHERE original_filename = ?
                ''', (filename,))
                row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'exists': True,
                    'doc_id': row['id'],
                    'filename': row['filename'],
                    'original_filename': row['original_filename'] if 'original_filename' in row.keys() else row['filename'],
                    'title': row['title'] or row['filename'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size']
                }
            
            return {'exists': False}
            
        except sqlite3.Error as e:
            logging.error(f"Error checking file existence: {e}")
            return {'exists': False, 'error': str(e)}
    
    def check_file_exists_by_pattern(self, pattern):
        """
        通过模式匹配检查文件是否存在
        
        Args:
            pattern: 文件名模式，可以是部分文件名
            
        Returns:
            dict: 包含是否存在及文档信息
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 使用LIKE操作符进行模糊匹配，同时检查filename和original_filename
            cursor.execute('''
            SELECT id, filename, original_filename, title, file_type, file_size 
            FROM documents 
            WHERE filename LIKE ? OR filename = ? OR original_filename LIKE ? OR original_filename = ?
            LIMIT 1
            ''', (f"%{pattern}", pattern, f"%{pattern}", pattern))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'exists': True,
                    'doc_id': row['id'],
                    'filename': row['filename'],
                    'original_filename': row['original_filename'] if 'original_filename' in row.keys() else row['filename'],
                    'title': row['title'] or row['filename'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size']
                }
            
            return {'exists': False}
            
        except sqlite3.Error as e:
            logging.error(f"Error checking file existence by pattern: {e}")
            return {'exists': False, 'error': str(e)}
    
    @staticmethod
    def get_file_type(filename):
        """根据文件名获取文件类型"""
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.pdf':
            return 'application/pdf'
        elif ext == '.docx':
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif ext == '.doc':
            return 'application/msword'
        elif ext == '.txt':
            return 'text/plain'
        else:
            return 'application/octet-stream'
    
    @staticmethod
    def format_file_size(size_bytes):
        """将文件大小格式化为人类可读形式"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.1f} GB"
    
    def process_batch_upload(self, files):
        """
        批量处理上传文件
        
        Args:
            files: 文件对象列表
            
        Returns:
            dict: 包含成功和失败文件的处理结果
        """
        results = {
            'success': [],
            'failed': []
        }
        
        for file in files:
            try:
                # 确保文件名安全
                filename = secure_filename(file.filename)
                
                # 检查文件类型
                ext = os.path.splitext(filename)[1].lower()[1:]
                if ext not in ALLOWED_EXTENSIONS:
                    results['failed'].append({
                        'filename': filename,
                        'error': f'不支持的文件类型: {ext}'
                    })
                    continue
                
                # 保存文件
                file_path = self.save_file(file)
                file_size = os.path.getsize(file_path)
                
                # 收集文件信息
                results['success'].append({
                    'filename': filename,
                    'path': file_path,
                    'size': file_size,
                    'type': self.get_file_type(filename)
                })
                
            except Exception as e:
                logging.error(f"处理文件 {file.filename} 失败: {e}")
                results['failed'].append({
                    'filename': file.filename,
                    'error': str(e)
                })
        
        return results
    
    def batch_add_documents(self, file_info_list, parsers):
        """
        批量添加文档到系统
        
        Args:
            file_info_list: 文件信息列表，每项包含文件路径、类型等
            parsers: 文档解析器字典，键为文件扩展名
            
        Returns:
            list: 添加的文档ID列表
        """
        doc_ids = []
        
        for file_info in file_info_list:
            try:
                # 解析文档内容
                file_path = file_info['path']
                file_ext = os.path.splitext(file_path)[1].lower()[1:]
                
                if file_ext not in parsers:
                    logging.error(f"不支持的文件类型: {file_ext}")
                    continue
                    
                parser = parsers[file_ext]
                doc_content = parser.parse(file_path)
                
                # 添加文档元数据
                title = doc_content['metadata'].get('title', file_info['filename'])
                doc_id = self.add_document_metadata(
                    filename=file_info['filename'],
                    filepath=file_path,
                    title=title,
                    file_type=file_info['type'],
                    file_size=file_info['size'],
                    metadata=doc_content['metadata']
                )
                
                doc_ids.append({
                    'id': doc_id,
                    'content': doc_content['text'],
                    'filename': file_info['filename']
                })
                
            except Exception as e:
                logging.error(f"添加文档失败: {e}")
                
        return doc_ids
    
    def update_document_metadata(self, doc_id, title=None, metadata=None):
        """
        更新文档元数据
        
        Args:
            doc_id: 文档ID
            title: 文档标题
            metadata: 文档元数据字典
            
        Returns:
            bool: 操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 准备更新字段
            update_fields = []
            params = []
            
            if title is not None:
                update_fields.append("title = ?")
                params.append(title)
                
            if metadata is not None:
                update_fields.append("metadata = ?")
                params.append(json.dumps(metadata))
                
            if not update_fields:
                logging.warning("没有提供要更新的字段")
                return False
                
            # 添加文档ID到参数列表
            params.append(doc_id)
            
            # 执行更新
            cursor.execute(
                f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ?",
                params
            )
            
            conn.commit()
            conn.close()
            
            logging.info(f"文档元数据更新成功: {doc_id}")
            return True
            
        except sqlite3.Error as e:
            logging.error(f"更新文档元数据失败: {e}")
            return False
    
    def add_document_content(self, doc_id, text_content, html_content=None):
        """
        添加或更新文档内容
        
        Args:
            doc_id: 文档ID
            text_content: 文本内容（用于搜索）
            html_content: HTML内容（用于显示）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在内容记录
            cursor.execute("SELECT 1 FROM document_content WHERE doc_id = ?", (doc_id,))
            exists = cursor.fetchone()
            
            if exists:
                # 更新现有记录 - 使用replace语法，因为FTS5表不支持UPDATE
                cursor.execute(
                    "DELETE FROM document_content WHERE doc_id = ?",
                    (doc_id,)
                )
                cursor.execute(
                    "INSERT INTO document_content (doc_id, content) VALUES (?, ?)",
                    (doc_id, text_content)
                )
                logging.info(f"更新文档内容: {doc_id}")
            else:
                # 插入新记录
                cursor.execute(
                    "INSERT INTO document_content (doc_id, content) VALUES (?, ?)",
                    (doc_id, text_content)
                )
                logging.info(f"添加文档内容: {doc_id}")
            
            # 处理HTML内容 - 存储在单独的表中
            if html_content:
                # 检查HTML内容是否已存在
                cursor.execute("SELECT 1 FROM document_html_content WHERE doc_id = ?", (doc_id,))
                html_exists = cursor.fetchone()
                
                if html_exists:
                    # 更新现有HTML内容
                    cursor.execute(
                        "UPDATE document_html_content SET html_content = ? WHERE doc_id = ?",
                        (html_content, doc_id)
                    )
                    logging.info(f"更新文档HTML内容: {doc_id}")
                else:
                    # 插入新的HTML内容
                    cursor.execute(
                        "INSERT INTO document_html_content (doc_id, html_content) VALUES (?, ?)",
                        (doc_id, html_content)
                    )
                    logging.info(f"添加文档HTML内容: {doc_id}")
            
            conn.commit()
            conn.close()
            
            return True
            
        except sqlite3.Error as e:
            logging.error(f"添加文档内容失败: {e}")
            return False 