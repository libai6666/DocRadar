"""
存储管理模块
负责文件存储和文档元数据管理
"""
import os
import json
import sqlite3
import logging
import shutil
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename
from app.core.config import UPLOADS_DIR, DATABASE_URI, ALLOWED_EXTENSIONS

class Storage:
    """存储管理类，负责文件存储和元数据管理"""
    
    def __init__(self, uploads_dir=UPLOADS_DIR, db_path=DATABASE_URI):
        """
        初始化存储管理器
        
        Args:
            uploads_dir: 文件上传目录
            db_path: 数据库文件路径
        """
        self.uploads_dir = uploads_dir
        self.db_path = db_path
        self._ensure_dirs()
        self.init_db()
    
    def _ensure_dirs(self):
        """确保必要的目录存在"""
        if not os.path.exists(self.uploads_dir):
            os.makedirs(self.uploads_dir, exist_ok=True)
    
    def init_db(self):
        """初始化数据库"""
        conn = None
        try:
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建文档元数据表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL UNIQUE,
                title TEXT,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                original_filename TEXT
            )
            ''')
            
            # 启用外键约束
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # 创建文档内容表（如果不存在）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_content'")
            if not cursor.fetchone():
                # 创建普通文档内容表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS document_content (
                    doc_id INTEGER PRIMARY KEY,
                    content TEXT,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
                ''')
                logging.info("创建document_content表")
            
            # 创建HTML内容表（如果不存在）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_html_content'")
            if not cursor.fetchone():
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS document_html_content (
                    doc_id INTEGER PRIMARY KEY,
                    html_content TEXT,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
                ''')
                
            conn.commit()
            logging.info("数据库初始化成功")
            
        except Exception as e:
            logging.error(f"初始化数据库失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def get_file_type(self, filename):
        """
        获取文件类型
        
        Args:
            filename: 文件名
            
        Returns:
            str: 文件类型
        """
        ext = os.path.splitext(filename)[1].lower()
        
        if ext == '.pdf':
            return 'pdf'
        elif ext in ['.docx', '.doc']:
            return 'word'
        elif ext == '.txt':
            return 'text'
        else:
            return 'unknown'
    
    def check_file_exists(self, filename):
        """
        检查文件是否已存在
        
        Args:
            filename: 文件名
            
        Returns:
            dict: 包含存在状态和文档ID的字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 查询数据库
            cursor.execute(
                "SELECT id, title, file_type, file_size, created_at FROM documents WHERE original_filename = ? OR filename = ?", 
                (filename, filename)
            )
            
            row = cursor.fetchone()
            
            if row:
                # 文件已存在，返回详细信息
                return {
                    'exists': True,
                    'doc_id': row['id'],
                    'title': row['title'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size'],
                    'created_at': row['created_at']
                }
            else:
                # 文件不存在
                return {
                    'exists': False
                }
                
        except Exception as e:
            logging.error(f"检查文件存在失败: {e}")
            return {
                'exists': False,
                'error': str(e)
            }
        finally:
            if conn:
                conn.close()
    
    def save_file(self, file, filename):
        """
        保存上传的文件
        
        Args:
            file: 文件对象
            filename: 安全处理后的文件名
            
        Returns:
            str: 文件保存路径
        """
        try:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(self.uploads_dir, safe_filename)
            
            # 保存文件
            file.save(file_path)
            logging.info(f"文件已保存: {file_path}")
            
            return file_path
            
        except Exception as e:
            logging.error(f"保存文件失败: {e}")
            raise
    
    def add_document_metadata(self, filename, filepath, title, file_type, file_size, metadata=None, original_filename=None):
        """
        添加文档元数据到数据库
        
        Args:
            filename: 文件名
            filepath: 文件路径
            title: 文档标题
            file_type: 文件类型
            file_size: 文件大小
            metadata: 元数据字典
            original_filename: 原始文件名
            
        Returns:
            int: 新添加的文档ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入文档元数据
            cursor.execute(
                '''
                INSERT INTO documents 
                (filename, filepath, title, file_type, file_size, metadata, original_filename) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    filename, 
                    filepath, 
                    title, 
                    file_type, 
                    file_size, 
                    json.dumps(metadata) if metadata else None,
                    original_filename or filename
                )
            )
            
            # 获取新插入的ID
            doc_id = cursor.lastrowid
            
            conn.commit()
            
            logging.info(f"添加文档元数据: {doc_id}")
            
            return doc_id
            
        except Exception as e:
            logging.error(f"添加文档元数据失败: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def update_document_metadata(self, doc_id, title=None, metadata=None):
        """
        更新文档元数据
        
        Args:
            doc_id: 文档ID
            title: 文档标题
            metadata: 元数据字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建更新SQL
            update_parts = []
            params = []
            
            if title is not None:
                update_parts.append("title = ?")
                params.append(title)
            
            if metadata is not None:
                update_parts.append("metadata = ?")
                params.append(json.dumps(metadata))
            
            if not update_parts:
                return True  # 没有更新内容
            
            # 添加ID条件
            params.append(doc_id)
            
            # 执行更新
            cursor.execute(
                f"UPDATE documents SET {', '.join(update_parts)} WHERE id = ?",
                params
            )
            
            conn.commit()
            
            logging.info(f"更新文档元数据: {doc_id}")
            
            return True
            
        except Exception as e:
            logging.error(f"更新文档元数据失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
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
            rows = cursor.fetchall()
            
            # 转换为字典列表
            for row in rows:
                documents.append(dict(row))
            
            # 获取总数（用于分页）
            count_sql = "SELECT COUNT(*) FROM documents"
            count_params = []
            
            if search_query:
                count_sql += " WHERE title LIKE ? OR filename LIKE ? OR original_filename LIKE ?"
                count_params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
                
            cursor.execute(count_sql, count_params)
            total_count = cursor.fetchone()[0]
            
            # 计算分页信息
            pagination = {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit if limit else 1,
                'has_prev': page > 1,
                'has_next': page < ((total_count + limit - 1) // limit if limit else 1)
            }
            
            return {
                'documents': documents,
                'pagination': pagination
            }
            
        except Exception as e:
            logging.error(f"获取文档列表失败: {e}")
            return {
                'documents': [],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': 0,
                    'pages': 0,
                    'has_prev': False,
                    'has_next': False
                }
            }
        finally:
            if conn:
                conn.close()
    
    def delete_document(self, doc_id):
        """
        删除文档及其内容
        
        Args:
            doc_id: 文档ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 首先获取文档信息
            cursor.execute("SELECT filepath, metadata FROM documents WHERE id = ?", (doc_id,))
            result = cursor.fetchone()
            
            if not result:
                logging.warning(f"要删除的文档不存在: {doc_id}")
                return False
                
            filepath, metadata_json = result
            
            # 删除数据库记录（document_content和document_html_content记录会通过外键级联删除）
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            
            # 删除文件
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # 删除相关的图片（如果是DOCX文档）
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                    if 'image_directory' in metadata and os.path.exists(metadata['image_directory']):
                        shutil.rmtree(metadata['image_directory'])
                        logging.info(f"删除文档图片目录: {metadata['image_directory']}")
                except Exception as e:
                    logging.error(f"删除文档图片失败: {e}")
            
            conn.commit()
            
            logging.info(f"删除文档成功: {doc_id}")
            
            return True
            
        except Exception as e:
            logging.error(f"删除文档失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
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
                # 更新现有记录
                cursor.execute(
                    "UPDATE document_content SET content = ? WHERE doc_id = ?",
                    (text_content, doc_id)
                )
                logging.info(f"更新文档内容: {doc_id}")
            else:
                # 插入新记录
                cursor.execute(
                    "INSERT INTO document_content (doc_id, content) VALUES (?, ?)",
                    (doc_id, text_content)
                )
                logging.info(f"添加文档内容: {doc_id}")
            
            # 处理HTML内容（如果有）
            if html_content:
                cursor.execute("SELECT 1 FROM document_html_content WHERE doc_id = ?", (doc_id,))
                html_exists = cursor.fetchone()
                
                if html_exists:
                    cursor.execute(
                        "UPDATE document_html_content SET html_content = ? WHERE doc_id = ?",
                        (html_content, doc_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO document_html_content (doc_id, html_content) VALUES (?, ?)",
                        (doc_id, html_content)
                    )
                logging.info(f"保存文档HTML内容: {doc_id}")
            
            conn.commit()
            
            return True
            
        except Exception as e:
            logging.error(f"添加文档内容失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def get_document_content(self, doc_id):
        """
        获取文档内容
        
        Args:
            doc_id: 文档ID
            
        Returns:
            dict: 包含文本内容和HTML内容的字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取文本内容
            cursor.execute("SELECT content FROM document_content WHERE doc_id = ?", (doc_id,))
            content_row = cursor.fetchone()
            
            text_content = content_row['content'] if content_row else ""
            
            # 获取HTML内容
            cursor.execute("SELECT html_content FROM document_html_content WHERE doc_id = ?", (doc_id,))
            html_row = cursor.fetchone()
            
            html_content = html_row['html_content'] if html_row else ""
            
            return {
                'text': text_content,
                'html': html_content
            }
            
        except Exception as e:
            logging.error(f"获取文档内容失败: {e}")
            return {
                'text': "",
                'html': ""
            }
        finally:
            if conn:
                conn.close()
    
    def get_mime_type(self, file_path):
        """
        获取文件的MIME类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: MIME类型
        """
        # 先通过扩展名判断
        ext = os.path.splitext(file_path)[1].lower()
        
        # 检查是否是已知的文件类型
        if ext in ALLOWED_EXTENSIONS:
            return ALLOWED_EXTENSIONS[ext]
        
        # 如果不是已知类型，使用mimetypes模块猜测
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return mime_type or 'application/octet-stream' 