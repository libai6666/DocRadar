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
import time
import random
from datetime import datetime
from werkzeug.utils import secure_filename
from app.core.config import UPLOADS_DIR, DATABASE_URI, ALLOWED_EXTENSIONS

# 添加临时目录常量
TEMP_DIR = os.path.join(os.path.dirname(UPLOADS_DIR), 'temp')

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
        
        # 初始化时清理临时文件
        self.cleanup_temp_files()
    
    def _ensure_dirs(self):
        """确保必要的目录存在"""
        if not os.path.exists(self.uploads_dir):
            os.makedirs(self.uploads_dir, exist_ok=True)
        
        # 确保临时目录存在
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, exist_ok=True)
            logging.info(f"创建临时目录: {TEMP_DIR}")
    
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
            
            # 规范化文件名以便进行比较
            normalized_filename = filename.lower()
            
            # 查询数据库 - 使用LOWER函数进行不区分大小写的比较
            cursor.execute(
                """
                SELECT 
                    id, title, file_type, file_size, created_at, original_filename, filename 
                FROM documents 
                WHERE LOWER(original_filename) = ? OR LOWER(filename) = ?
                """, 
                (normalized_filename, normalized_filename)
            )
            
            row = cursor.fetchone()
            
            if row:
                # 文件已存在，返回详细信息
                return {
                    'exists': True,
                    'doc_id': row['id'],
                    'id': row['id'],  # 添加id字段，确保与doc_id一致
                    'title': row['title'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size'],
                    'created_at': row['created_at'],
                    'original_filename': row['original_filename'],
                    'filename': row['filename']
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
    
    def cleanup_temp_files(self, max_age_hours=24):
        """
        清理临时目录中的旧文件
        
        Args:
            max_age_hours: 文件最大保留时间（小时）
            
        Returns:
            int: 清理的文件数量
        """
        if not os.path.exists(TEMP_DIR):
            return 0
            
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        try:
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                
                # 跳过目录
                if os.path.isdir(file_path):
                    continue
                    
                # 检查文件年龄
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except Exception as e:
                        logging.warning(f"清理临时文件失败: {file_path}, 错误: {e}")
            
            if cleaned_count > 0:
                logging.info(f"已清理 {cleaned_count} 个临时文件")
                
            return cleaned_count
        except Exception as e:
            logging.error(f"清理临时文件过程中发生错误: {e}")
            return 0
    
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
            
            # 每次保存文件时尝试清理临时文件
            self.cleanup_temp_files()
            
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
            
            # 确保标题不为空，如果为空则使用原始文件名（去掉扩展名）
            if not title or not title.strip():
                display_filename = original_filename or filename
                title = os.path.splitext(display_filename)[0]
                logging.info(f"文档标题为空，使用文件名作为标题: {title}")
            
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
                # 确保标题不为空
                if title and title.strip():
                    update_parts.append("title = ?")
                    params.append(title)
                else:
                    logging.warning(f"更新文档 {doc_id} 时传入了空标题，忽略标题更新")
            
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
    
    def safe_delete_file(self, file_path, max_retries=3, retry_delay=1.0):
        """
        安全删除文件，包含重试机制和临时目录处理
        
        Args:
            file_path: 要删除的文件路径
            max_retries: 最大重试次数
            retry_delay: 重试间隔时间(秒)
            
        Returns:
            bool: 删除是否成功
        """
        if not os.path.exists(file_path):
            logging.warning(f"要删除的文件不存在: {file_path}")
            return True  # 文件不存在视为删除成功
        
        # 尝试直接删除
        for attempt in range(max_retries):
            try:
                os.remove(file_path)
                logging.info(f"成功删除文件: {file_path}")
                return True
            except PermissionError as e:
                logging.warning(f"删除文件失败(尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 添加随机延迟，避免多个进程同时尝试
                    time.sleep(retry_delay + random.random())
                    continue
            except Exception as e:
                logging.error(f"删除文件时发生未知错误: {e}")
                break
        
        # 如果直接删除失败，尝试移动到临时目录
        try:
            # 生成唯一的临时文件名
            temp_filename = f"del_{int(time.time())}_{os.path.basename(file_path)}"
            temp_path = os.path.join(TEMP_DIR, temp_filename)
            
            # 移动文件到临时目录
            shutil.move(file_path, temp_path)
            logging.info(f"文件已移动到临时目录: {temp_path}")
            
            return True
        except Exception as e:
            logging.error(f"移动文件到临时目录失败: {e}")
            return False
    
    def delete_document(self, doc_id):
        """
        删除文档及其内容
        
        Args:
            doc_id: 文档ID
            
        Returns:
            bool: 删除是否成功
        """
        conn = None
        file_deleted = False
        db_deleted = False
        
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
            
            # 尝试删除文件
            if filepath and os.path.exists(filepath):
                file_deleted = self.safe_delete_file(filepath)
                if not file_deleted:
                    logging.warning(f"文件删除失败，但将继续删除数据库记录: {filepath}")
            else:
                # 文件不存在视为删除成功
                file_deleted = True
            
            # 删除相关的图片（如果是DOCX文档）
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                    if 'image_directory' in metadata and os.path.exists(metadata['image_directory']):
                        try:
                            shutil.rmtree(metadata['image_directory'])
                            logging.info(f"删除文档图片目录: {metadata['image_directory']}")
                        except Exception as e:
                            logging.error(f"删除文档图片目录失败: {e}")
                except Exception as e:
                    logging.error(f"处理文档元数据失败: {e}")
            
            # 无论文件删除是否成功，都删除数据库记录
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            db_deleted = True
            
            logging.info(f"删除文档成功: {doc_id}, 文件删除: {file_deleted}, 数据库删除: {db_deleted}")
            
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