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
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from app.core.config import UPLOADS_DIR, DATABASE_URI, ALLOWED_EXTENSIONS, DOCUMENT_IMAGES_DIR

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
        
        # 启动时清理临时文件，使用较短的过期时间
        cleaned = self.cleanup_temp_files(max_age_hours=1)
        if cleaned > 0:
            logging.info(f"启动时清理了 {cleaned} 个临时文件")
    
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
                original_filename TEXT,
                document_date TEXT
            )
            ''')
            
            # 检查是否需要添加document_date列
            cursor.execute("PRAGMA table_info(documents)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'document_date' not in columns:
                logging.info("添加document_date列到documents表")
                cursor.execute("ALTER TABLE documents ADD COLUMN document_date TEXT")
            
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
                    id, title, file_type, file_size, created_at, original_filename, filename, document_date 
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
                    'document_date': row['document_date'],
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
            os.makedirs(TEMP_DIR, exist_ok=True)
            logging.info(f"创建临时目录: {TEMP_DIR}")
            return 0
            
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        mark_files_processed = 0
        
        try:
            # 处理标记文件（包含需要删除的文件路径）
            mark_files = [f for f in os.listdir(TEMP_DIR) if f.startswith('mark_del_') and f.endswith('.txt')]
            for mark_file in mark_files:
                mark_path = os.path.join(TEMP_DIR, mark_file)
                
                try:
                    # 检查标记文件的年龄
                    file_age = now - os.path.getmtime(mark_path)
                    
                    # 只处理超过1小时的标记文件，避免处理刚创建的
                    if file_age > 3600:
                        try:
                            # 读取标记文件中的文件路径
                            with open(mark_path, 'r') as f:
                                target_path = f.read().strip()
                            
                            # 检查目标文件是否存在
                            if os.path.exists(target_path):
                                # 检查文件是否被锁定
                                if not self._is_file_locked(target_path):
                                    # 尝试删除目标文件
                                    try:
                                        os.remove(target_path)
                                        logging.info(f"成功删除标记的文件: {target_path}")
                                        cleaned_count += 1
                                    except Exception as e:
                                        logging.warning(f"删除标记的文件失败: {target_path}, 错误: {e}")
                            
                            # 删除标记文件
                            os.remove(mark_path)
                            mark_files_processed += 1
                            logging.info(f"处理并删除标记文件: {mark_path}")
                        except Exception as e:
                            logging.error(f"处理标记文件失败: {mark_path}, 错误: {e}")
                except Exception as e:
                    logging.error(f"检查标记文件时出错: {mark_path}, 错误: {e}")
            
            # 处理临时文件
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                
                # 跳过目录和标记文件
                if os.path.isdir(file_path) or filename.startswith('mark_del_'):
                    continue
                    
                # 检查文件年龄
                try:
                    file_age = now - os.path.getmtime(file_path)
                    
                    # 对于temp_开头的文件（上传临时文件）使用较短的过期时间
                    if filename.startswith('temp_') and file_age > 3600:  # 1小时
                        self._try_delete_temp_file(file_path, cleaned_count)
                    # 对于del_开头的文件（删除失败的文件）使用中等过期时间
                    elif filename.startswith('del_') and file_age > 7200:  # 2小时
                        self._try_delete_temp_file(file_path, cleaned_count)
                    # 对于old_开头的文件（旧版本文件）使用较长的过期时间
                    elif filename.startswith('old_') and file_age > 14400:  # 4小时
                        self._try_delete_temp_file(file_path, cleaned_count)
                    # 其他所有临时文件使用默认过期时间
                    elif file_age > max_age_seconds:
                        self._try_delete_temp_file(file_path, cleaned_count)
                except Exception as e:
                    logging.warning(f"检查临时文件年龄失败: {file_path}, 错误: {e}")
            
            if cleaned_count > 0 or mark_files_processed > 0:
                logging.info(f"已清理 {cleaned_count} 个临时文件, 处理 {mark_files_processed} 个标记文件")
                
            return cleaned_count
        except Exception as e:
            logging.error(f"清理临时文件过程中发生错误: {e}")
            return 0
    
    def _try_delete_temp_file(self, file_path, cleaned_count):
        """
        尝试删除临时文件
        
        Args:
            file_path: 文件路径
            cleaned_count: 已清理的文件计数引用
            
        Returns:
            bool: 是否成功删除
        """
        try:
            # 检查文件是否被锁定
            if not self._is_file_locked(file_path):
                os.remove(file_path)
                cleaned_count += 1
                logging.info(f"清理临时文件: {file_path}")
                return True
            else:
                logging.warning(f"临时文件被锁定，无法清理: {file_path}")
                return False
        except Exception as e:
            logging.warning(f"清理临时文件失败: {file_path}, 错误: {e}")
            return False
    
    def save_file(self, file, filename, is_overwrite=False):
        """
        保存上传的文件
        
        Args:
            file: 文件对象
            filename: 安全处理后的文件名
            is_overwrite: 是否是覆盖模式上传
            
        Returns:
            str: 文件保存路径
        """
        try:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # 在覆盖模式下，使用特殊前缀标记临时文件
            prefix = "temp_" if is_overwrite else ""
            safe_filename = f"{prefix}{timestamp}_{filename}"
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
    
    def replace_file(self, old_doc_id, new_filepath, new_filename, original_filename, file_type, file_size, metadata=None):
        """
        安全替换文件（用于文件覆盖操作）
        
        Args:
            old_doc_id: 旧文档ID
            new_filepath: 新文件路径
            new_filename: 新文件名
            original_filename: 原始文件名
            file_type: 文件类型
            file_size: 文件大小
            metadata: 元数据字典
            
        Returns:
            dict: 包含操作结果和新文档ID
        """
        conn = None
        try:
            # 首先获取旧文档信息
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT filepath, title FROM documents WHERE id = ?", (old_doc_id,))
            result = cursor.fetchone()
            
            if not result:
                logging.warning(f"要替换的文档不存在: {old_doc_id}")
                # 如果旧文档不存在，则作为新文档处理
                doc_id = self.add_document_metadata(
                    filename=os.path.basename(new_filepath),
                    filepath=new_filepath,
                    title=os.path.splitext(original_filename)[0],
                    file_type=file_type,
                    file_size=file_size,
                    metadata=metadata,
                    original_filename=original_filename
                )
                return {
                    'success': True,
                    'doc_id': doc_id,
                    'replaced': False,
                    'message': '旧文档不存在，已作为新文档添加'
                }
            
            old_filepath, old_title = result
            
            # 新的文件替换策略：
            # 1. 不直接删除旧文件，而是先更新数据库记录
            # 2. 然后将旧文件标记为待删除，由清理任务处理
            # 3. 这样即使旧文件被锁定，也不会影响覆盖操作
            
            # 更新数据库记录
            cursor.execute(
                """
                UPDATE documents 
                SET filename = ?, filepath = ?, file_type = ?, file_size = ?, 
                    metadata = ?, original_filename = ?
                WHERE id = ?
                """,
                (
                    os.path.basename(new_filepath),
                    new_filepath,
                    file_type,
                    file_size,
                    json.dumps(metadata) if metadata else None,
                    original_filename,
                    old_doc_id
                )
            )
            
            conn.commit()
            
            # 异步处理旧文件：如果存在，将其移动到临时目录等待清理
            if old_filepath and os.path.exists(old_filepath) and old_filepath != new_filepath:
                try:
                    # 生成临时文件名
                    temp_filename = f"old_{int(time.time())}_{os.path.basename(old_filepath)}"
                    temp_path = os.path.join(TEMP_DIR, temp_filename)
                    
                    # 确保临时目录存在
                    if not os.path.exists(TEMP_DIR):
                        os.makedirs(TEMP_DIR, exist_ok=True)
                    
                    # 尝试移动旧文件到临时目录
                    try:
                        shutil.move(old_filepath, temp_path)
                        logging.info(f"旧文件已移动到临时目录: {temp_path}")
                    except (PermissionError, OSError) as e:
                        # 如果移动失败，记录但不中断流程
                        logging.warning(f"移动旧文件到临时目录失败: {e}")
                        
                        # 创建一个标记文件，记录需要清理的文件路径
                        mark_filename = f"mark_del_{int(time.time())}_{os.path.basename(old_filepath)}.txt"
                        mark_path = os.path.join(TEMP_DIR, mark_filename)
                        try:
                            with open(mark_path, 'w') as f:
                                f.write(old_filepath)
                            logging.info(f"已创建文件删除标记: {mark_path}")
                        except Exception as mark_err:
                            logging.error(f"创建文件删除标记失败: {mark_err}")
                except Exception as e:
                    logging.warning(f"处理旧文件时出错，但不影响覆盖操作: {e}")
            
            logging.info(f"文件替换成功: {old_doc_id}, 新文件: {new_filepath}")
            
            return {
                'success': True,
                'doc_id': old_doc_id,
                'replaced': True,
                'message': '文件替换成功'
            }
            
        except Exception as e:
            logging.error(f"替换文件失败: {e}")
            if conn:
                conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': '替换文件失败'
            }
        finally:
            if conn:
                conn.close()
    
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
            
            # 提取文档日期
            document_date = None
            if metadata and isinstance(metadata, dict) and 'document_date' in metadata:
                document_date = metadata['document_date']
            
            # 插入文档元数据
            cursor.execute(
                '''
                INSERT INTO documents 
                (filename, filepath, title, file_type, file_size, metadata, original_filename, document_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    filename, 
                    filepath, 
                    title, 
                    file_type, 
                    file_size, 
                    json.dumps(metadata) if metadata else None,
                    original_filename or filename,
                    document_date
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
                id, filename, filepath, title, file_type, file_size, created_at, original_filename, document_date 
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
        
        # 检查文件是否被锁定
        file_locked = self._is_file_locked(file_path)
        if file_locked:
            logging.warning(f"文件被锁定，无法直接删除: {file_path}")
            return self._handle_locked_file(file_path)
        
        # 尝试直接删除
        for attempt in range(max_retries):
            try:
                os.remove(file_path)
                logging.info(f"成功删除文件: {file_path}")
                return True
            except PermissionError as e:
                logging.warning(f"删除文件失败(尝试 {attempt+1}/{max_retries}): {e}")
                
                # 检查是否是最后一次尝试
                if attempt < max_retries - 1:
                    # 添加随机延迟，避免多个进程同时尝试
                    delay_time = retry_delay + random.random()
                    logging.info(f"等待 {delay_time:.2f} 秒后重试...")
                    time.sleep(delay_time)
                    
                    # 重新检查文件是否被锁定
                    if self._is_file_locked(file_path):
                        logging.warning(f"检测到文件被锁定，跳过后续删除尝试: {file_path}")
                        return self._handle_locked_file(file_path)
                else:
                    # 最后一次尝试也失败，处理锁定文件
                    return self._handle_locked_file(file_path)
            except Exception as e:
                logging.error(f"删除文件时发生未知错误: {e}")
                break
        
        # 如果所有尝试都失败，处理锁定文件
        return self._handle_locked_file(file_path)
    
    def _is_file_locked(self, file_path):
        """
        检查文件是否被锁定
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否被锁定
        """
        if not os.path.exists(file_path):
            return False
        
        try:
            # 尝试以写入模式打开文件
            with open(file_path, 'a+b') as f:
                # 尝试获取文件锁
                try:
                    # Windows平台
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                        # 如果成功获取锁，释放它
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    # Unix/Linux平台
                    else:
                        import fcntl
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        # 如果成功获取锁，释放它
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    return False  # 文件未被锁定
                except (IOError, OSError):
                    return True  # 文件被锁定
        except (IOError, OSError):
            return True  # 无法打开文件，视为被锁定
    
    def _handle_locked_file(self, file_path):
        """
        处理被锁定的文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 确保临时目录存在
            if not os.path.exists(TEMP_DIR):
                os.makedirs(TEMP_DIR, exist_ok=True)
            
            # 尝试移动到临时目录
            try:
                # 生成唯一的临时文件名
                temp_filename = f"del_{int(time.time())}_{os.path.basename(file_path)}"
                temp_path = os.path.join(TEMP_DIR, temp_filename)
                
                # 尝试移动文件
                try:
                    shutil.move(file_path, temp_path)
                    logging.info(f"文件已移动到临时目录: {temp_path}")
                    return True
                except (PermissionError, OSError) as e:
                    logging.warning(f"移动文件到临时目录失败: {e}")
            except Exception as e:
                logging.error(f"处理锁定文件时出错: {e}")
            
            # 如果移动失败，创建一个标记文件
            mark_filename = f"mark_del_{int(time.time())}_{os.path.basename(file_path)}.txt"
            mark_path = os.path.join(TEMP_DIR, mark_filename)
            try:
                with open(mark_path, 'w') as f:
                    f.write(file_path)
                logging.info(f"已创建文件删除标记: {mark_path}")
                return True  # 创建标记成功，视为处理成功
            except Exception as e:
                logging.error(f"创建文件删除标记失败: {e}")
                
            return False  # 所有处理方法都失败
        except Exception as e:
            logging.error(f"处理锁定文件的过程中发生错误: {e}")
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
                    # 检查旧格式的图片目录
                    if 'image_directory' in metadata and os.path.exists(metadata['image_directory']):
                        try:
                            shutil.rmtree(metadata['image_directory'])
                            logging.info(f"删除文档图片目录: {metadata['image_directory']}")
                        except Exception as e:
                            logging.error(f"删除文档图片目录失败: {e}")
                    
                    # 查找并删除新格式的图片目录
                    if os.path.exists(DOCUMENT_IMAGES_DIR):
                        # 查找所有可能的年月子目录
                        for year_month_dir in os.listdir(DOCUMENT_IMAGES_DIR):
                            doc_image_dir = os.path.join(DOCUMENT_IMAGES_DIR, year_month_dir, str(doc_id))
                            if os.path.exists(doc_image_dir):
                                try:
                                    shutil.rmtree(doc_image_dir)
                                    logging.info(f"删除文档图片目录: {doc_image_dir}")
                                except Exception as e:
                                    logging.error(f"删除文档图片目录失败: {e}")
                except Exception as e:
                    logging.error(f"处理文档元数据失败: {e}")
            
            # 无论文件删除是否成功，都删除数据库记录
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            cursor.execute("DELETE FROM document_content WHERE doc_id = ?", (doc_id,))
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
    
    def find_latest_document_by_filename(self, filename, fuzzy_match=False):
        """
        查找最新上传的同名或相似文档
        
        Args:
            filename: 文件名
            fuzzy_match: 是否启用模糊匹配
            
        Returns:
            int or None: 文档ID，如果找不到则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 规范化文件名以便进行比较
            normalized_filename = filename.lower() if filename else ""
            
            if not normalized_filename:
                return None
            
            # 先尝试精确匹配
            cursor.execute(
                """
                SELECT id 
                FROM documents 
                WHERE LOWER(original_filename) = ? OR LOWER(filename) = ?
                ORDER BY created_at DESC
                LIMIT 1
                """, 
                (normalized_filename, normalized_filename)
            )
            
            row = cursor.fetchone()
            
            if row:
                return row[0]
            
            # 如果启用模糊匹配且精确匹配没有结果
            if fuzzy_match:
                # 移除版本号等常见后缀进行匹配
                # 例如：从 "文档v1.0.pdf" 提取 "文档"
                base_name = re.sub(r'[_\s-]?v\d+(\.\d+)*|[_\s-]?\d+(\.\d+)*$', '', 
                                   os.path.splitext(normalized_filename)[0])
                
                if len(base_name) > 3:  # 确保基础名称足够长，避免过于宽泛的匹配
                    search_pattern = f"{base_name}%"
                    
                    cursor.execute(
                        """
                        SELECT id 
                        FROM documents 
                        WHERE LOWER(original_filename) LIKE ? OR LOWER(filename) LIKE ?
                        ORDER BY created_at DESC
                        LIMIT 1
                        """, 
                        (search_pattern, search_pattern)
                    )
                    
                    row = cursor.fetchone()
                    
                    if row:
                        logging.info(f"通过模糊匹配找到相似文档: 原始='{filename}', 基础名称='{base_name}'")
                        return row[0]
            
            return None
                
        except Exception as e:
            logging.error(f"查找同名文档失败: {e}")
            return None
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