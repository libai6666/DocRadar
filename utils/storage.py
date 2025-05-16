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
    
    def add_document_metadata(self, filename, filepath, title, file_type, file_size, metadata=None):
        """
        添加文档元数据到数据库
        
        Args:
            filename: 原始文件名
            filepath: 存储的文件路径
            title: 文档标题
            file_type: 文件类型
            file_size: 文件大小
            metadata: 文档元数据字典
            
        Returns:
            int: 文档ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 序列化元数据为JSON
            metadata_json = json.dumps(metadata) if metadata else None
            
            # 插入元数据
            cursor.execute('''
            INSERT INTO documents 
                (filename, filepath, title, file_type, file_size, metadata)
            VALUES 
                (?, ?, ?, ?, ?, ?)
            ''', (filename, filepath, title, file_type, file_size, metadata_json))
            
            doc_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logging.info(f"Document metadata added with ID: {doc_id}")
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
            cursor.execute("SELECT filepath, metadata FROM documents WHERE id = ?", (doc_id,))
            result = cursor.fetchone()
            
            if not result:
                logging.warning(f"Document not found: {doc_id}")
                conn.close()
                return False
                
            filepath = result['filepath']
            
            # 检查是否有图片目录需要清理
            try:
                if result['metadata']:
                    metadata = json.loads(result['metadata'])
                    # 清理文档关联的图片目录
                    if metadata and 'image_directory' in metadata:
                        image_dir = metadata['image_directory']
                        if os.path.exists(image_dir) and os.path.isdir(image_dir):
                            shutil.rmtree(image_dir)
                            logging.info(f"Removed image directory: {image_dir}")
            except Exception as e:
                logging.error(f"Error cleaning up image directory: {e}")
                # 继续处理文档删除，不因图片清理失败而中断
            
            # 删除文件记录
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            cursor.execute("DELETE FROM document_content WHERE doc_id = ?", (doc_id,))
            
            conn.commit()
            conn.close()
            
            # 删除物理文件
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info(f"File deleted: {filepath}")
            
            logging.info(f"Document deleted: {doc_id}")
            return True
            
        except (sqlite3.Error, OSError) as e:
            logging.error(f"Error deleting document: {e}")
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
                id, filename, filepath, title, file_type, file_size, created_at 
            FROM 
                documents 
            '''
            
            params = []
            
            # 添加搜索条件
            if search_query:
                sql += "WHERE title LIKE ? OR filename LIKE ? "
                params.extend([f'%{search_query}%', f'%{search_query}%'])
            
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
                    'created_at': row['created_at']
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
            
            cursor.execute('''
            SELECT id, filename, title, file_type, file_size 
            FROM documents 
            WHERE filename = ?
            ''', (filename,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'exists': True,
                    'doc_id': row['id'],
                    'filename': row['filename'],
                    'title': row['title'] or row['filename'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size']
                }
            
            return {'exists': False}
            
        except sqlite3.Error as e:
            logging.error(f"Error checking file existence: {e}")
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