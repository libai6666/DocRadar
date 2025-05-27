"""
搜索引擎模块 - 基于标准SQL LIKE查询
使用常规SQL LIKE查询实现基本搜索功能
"""
import sqlite3
import logging
import re
import os
from app.core.config import DATABASE_URI, PREVIEW_LENGTH, SEARCH_RESULT_LIMIT

class SearchEngine:
    """基于SQL LIKE的搜索引擎 - 不使用FTS5"""
    
    def __init__(self, db_path=DATABASE_URI):
        """
        初始化搜索引擎
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        """初始化数据库和文档内容表 - 只使用标准SQL表"""
        conn = None
        try:
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path.replace('file:', '').split('?')[0])
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
            
            # 检查是否需要添加original_filename列到documents表
            cursor.execute("PRAGMA table_info(documents)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'original_filename' not in column_names:
                logging.info("添加original_filename列到documents表")
                cursor.execute("ALTER TABLE documents ADD COLUMN original_filename TEXT")
            
            # 检查document_content表是否存在
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
            
            # 检查document_html_content表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_html_content'")
            if not cursor.fetchone():
                # 创建HTML内容表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS document_html_content (
                    doc_id INTEGER PRIMARY KEY,
                    html_content TEXT,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
                ''')
                logging.info("创建document_html_content表")
            
            conn.commit()
            logging.info("搜索引擎数据库初始化成功")
            
        except Exception as e:
            logging.error(f"初始化数据库失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def index_document(self, doc_id, title, content, file_type):
        """
        将文档内容添加到搜索索引
        
        Args:
            doc_id: 文档ID
            title: 文档标题
            content: 文档内容
            file_type: 文件类型
            
        Returns:
            bool: 索引是否成功
        """
        # 注意：此函数不再需要，索引操作已转移到Storage类中的add_document_content方法
        logging.info(f"文档 {doc_id} 索引请求 - 操作已转移到Storage类")
        return True
    
    def search(self, query, limit=SEARCH_RESULT_LIMIT):
        """
        搜索文档
        
        Args:
            query: 搜索关键词
            limit: 最大结果数量
            
        Returns:
            list: 搜索结果列表
        """
        if not query:
            return []
            
        results = []
        
        try:
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 使用LIKE搜索
            sql = '''
            SELECT 
                d.id, d.title, d.file_type, d.file_size, d.created_at, d.original_filename,
                dc.content
            FROM 
                documents d
            JOIN 
                document_content dc ON d.id = dc.doc_id
            WHERE 
                d.title LIKE ? OR
                dc.content LIKE ?
            ORDER BY 
                d.created_at DESC
            LIMIT ?
            '''
            
            search_pattern = f"%{query}%"
            cursor.execute(sql, (search_pattern, search_pattern, limit))
            rows = cursor.fetchall()
            
            # 处理搜索结果
            for row in rows:
                content = row['content']
                preview = self._generate_preview(content, query)
                
                # 确保title字段有值
                title = row['title']
                original_title = title  # 保存原始标题，用于日志记录
                
                if not title or title.strip() == '':
                    # 如果标题为空，使用原始文件名
                    if row['original_filename'] and row['original_filename'].strip() != '':
                        title = os.path.splitext(row['original_filename'])[0]
                        logging.info(f"文档ID {row['id']}: 标题为空，使用原始文件名 '{row['original_filename']}' 作为标题")
                    else:
                        # 如果原始文件名也为空，使用默认标题
                        title = f"无标题文档 #{row['id']}"
                        logging.info(f"文档ID {row['id']}: 标题和原始文件名均为空，使用默认标题 '{title}'")
                else:
                    logging.info(f"文档ID {row['id']}: 使用原始标题 '{title}'")
                
                result = {
                    'id': row['id'],
                    'title': title,  # 使用处理后的标题
                    'file_type': row['file_type'],
                    'file_size': row['file_size'],
                    'created_at': row['created_at'],
                    'original_filename': row['original_filename'],
                    'preview': preview
                }
                results.append(result)
            
            logging.info(f"搜索 '{query}' 找到 {len(results)} 个结果")
            
        except Exception as e:
            logging.error(f"搜索失败: {e}")
        finally:
            if conn:
                conn.close()
                
        return results
    
    def _generate_preview(self, content, query):
        """
        根据搜索词生成内容预览
        
        Args:
            content: 文档内容
            query: 搜索关键词
            
        Returns:
            str: 带有高亮的预览内容
        """
        try:
            # 基本清理
            content = content.replace('\n', ' ').strip()
            
            # 查找搜索词的位置
            lower_content = content.lower()
            lower_query = query.lower()
            
            positions = []
            start_pos = 0
            while True:
                pos = lower_content.find(lower_query, start_pos)
                if pos == -1:
                    break
                positions.append(pos)
                start_pos = pos + len(query)
            
            # 如果找不到精确匹配，使用模糊匹配
            if not positions:
                words = query.lower().split()
                for word in words:
                    if len(word) > 2:  # 忽略太短的词
                        start_pos = 0
                        while True:
                            pos = lower_content.find(word, start_pos)
                            if pos == -1:
                                break
                            positions.append(pos)
                            start_pos = pos + len(word)
            
            # 如果仍然找不到，返回内容开头
            if not positions:
                preview_len = min(PREVIEW_LENGTH, len(content))
                return content[:preview_len] + "..."
            
            # 找到最佳片段位置
            best_pos = min(positions)
            
            # 计算预览的起始和结束位置
            half_len = PREVIEW_LENGTH // 2
            start = max(0, best_pos - half_len)
            end = min(len(content), best_pos + half_len)
            
            # 调整到单词边界
            if start > 0:
                while start > 0 and content[start] != ' ':
                    start -= 1
                
            if end < len(content):
                while end < len(content) and content[end] != ' ':
                    end += 1
                if end < len(content):
                    end += 1
            
            # 提取预览内容
            preview = content[start:end]
            
            # 添加省略号
            if start > 0:
                preview = "..." + preview
            if end < len(content):
                preview = preview + "..."
            
            # 高亮搜索词
            preview = self.highlight_text(preview, query)
            
            return preview
            
        except Exception as e:
            logging.error(f"生成预览失败: {e}")
            return content[:PREVIEW_LENGTH] + "..."
    
    def highlight_text(self, text, query):
        """
        高亮文本中的搜索词
        
        Args:
            text: 原始文本
            query: 搜索词
            
        Returns:
            str: 高亮后的文本
        """
        try:
            # 单词边界模式，适合英文
            pattern = r'\b(' + re.escape(query) + r')\b'
            highlighted = re.sub(pattern, r'<mark>\1</mark>', text, flags=re.IGNORECASE)
            
            # 如果没有找到匹配，使用宽松模式（适合中文等）
            if '<mark>' not in highlighted:
                pattern = re.escape(query)
                highlighted = re.sub(pattern, lambda m: f"<mark>{m.group(0)}</mark>", text, flags=re.IGNORECASE)
            
            # 如果还是没有找到，尝试单词匹配
            if '<mark>' not in highlighted:
                words = query.split()
                for word in words:
                    if len(word) > 2:  # 忽略太短的词
                        pattern = re.escape(word)
                        highlighted = re.sub(pattern, lambda m: f"<mark>{m.group(0)}</mark>", highlighted, flags=re.IGNORECASE)
            
            return highlighted
            
        except Exception as e:
            logging.error(f"高亮文本失败: {e}")
            return text
    
    def highlight_content(self, content, query):
        """
        高亮文档内容中的搜索词
        
        Args:
            content: 文档内容
            query: 搜索词
            
        Returns:
            str: 高亮后的文档内容
        """
        try:
            # 处理HTML文档
            if content.startswith('<') and content.endswith('>'):
                # 简单的HTML标签检测
                # 为了避免影响HTML结构，我们需要更谨慎地处理
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # 只处理文本节点
                for text_node in soup.find_all(text=True):
                    if text_node.parent.name not in ['script', 'style']:
                        highlighted_text = self.highlight_text(text_node, query)
                        # 只有当文本实际发生变化时才替换
                        if highlighted_text != text_node:
                            new_tag = soup.new_string(highlighted_text)
                            text_node.replace_with(new_tag)
                
                return str(soup)
            else:
                # 对于纯文本，直接处理
                return self.highlight_text(content, query)
                
        except Exception as e:
            logging.error(f"高亮内容失败: {e}")
            return content
    
    def get_document_by_id(self, doc_id, original_filename_from_url=None):
        """
        通过ID获取文档，如果找不到则尝试查找同名或相似文档
        
        Args:
            doc_id: 文档ID
            original_filename_from_url: 从URL参数获取的原始文件名（可选）
            
        Returns:
            dict: 文档信息
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取文档基本信息
            cursor.execute('''
            SELECT 
                d.id, d.title, d.file_type, d.file_size, d.created_at, d.filename, d.filepath, d.original_filename, d.metadata,
                dc.content
            FROM 
                documents d
            LEFT JOIN 
                document_content dc ON d.id = dc.doc_id
            WHERE 
                d.id = ?
            ''', (doc_id,))
            
            row = cursor.fetchone()
            
            if not row:
                # 文档不存在，尝试查找是否有同名文档被重新上传
                logging.info(f"文档ID {doc_id} 不存在，尝试查找替代文档")
                
                # 首先尝试使用URL参数中的原始文件名
                original_filename = original_filename_from_url
                
                # 如果URL中没有提供，再尝试从session中的搜索历史获取
                if not original_filename:
                    from flask import session
                    
                    if 'search_history' in session:
                        search_history = session['search_history']
                        for history_item in search_history:
                            for result in history_item.get('results', []):
                                if result.get('id') == doc_id and 'original_filename' in result:
                                    original_filename = result['original_filename']
                                    logging.info(f"从搜索历史中找到文档ID {doc_id} 的原始文件名: {original_filename}")
                                    break
                            if original_filename:
                                break
                
                # 如果找到了原始文件名，尝试查找同名文档
                if original_filename:
                    # 使用Storage类查找最新上传的同名文档
                    from app.utils.storage import Storage
                    storage = Storage()
                    
                    # 先尝试精确匹配
                    new_doc_id = storage.find_latest_document_by_filename(original_filename)
                    
                    # 如果精确匹配失败，尝试模糊匹配
                    if not new_doc_id:
                        logging.info(f"未找到与 '{original_filename}' 精确匹配的文档，尝试模糊匹配")
                        new_doc_id = storage.find_latest_document_by_filename(original_filename, fuzzy_match=True)
                    
                    if new_doc_id:
                        logging.info(f"找到与文档ID {doc_id} 同名或相似的新上传文档: ID={new_doc_id}")
                        
                        # 重新查询新文档的信息
                        cursor.execute('''
                        SELECT 
                            d.id, d.title, d.file_type, d.file_size, d.created_at, d.filename, d.filepath, d.original_filename, d.metadata,
                            dc.content
                        FROM 
                            documents d
                        LEFT JOIN 
                            document_content dc ON d.id = dc.doc_id
                        WHERE 
                            d.id = ?
                        ''', (new_doc_id,))
                        
                        row = cursor.fetchone()
                        
                        if not row:
                            logging.warning(f"找到的新文档ID {new_doc_id} 无法获取详细信息")
                            return None
                        else:
                            # 将原始文件名添加到文档信息中，用于后续判断匹配类型
                            document = dict(row)
                            document['search_original_filename'] = original_filename
                            row = document
                    else:
                        logging.info(f"找不到与文档ID {doc_id} 同名或相似的新上传文档")
                        return None
                else:
                    # 没有找到原始文件名，无法查找同名文档
                    logging.info(f"无法找到文档ID {doc_id} 的原始文件名，无法查找同名文档")
                    return None
                
            document = dict(row)
            
            # 确保title字段有值
            original_title = document['title']  # 保存原始标题，用于日志记录
            
            if not document['title'] or document['title'].strip() == '':
                # 如果标题为空，使用原始文件名
                if document['original_filename'] and document['original_filename'].strip() != '':
                    document['title'] = os.path.splitext(document['original_filename'])[0]
                    logging.info(f"文档ID {document['id']}: 标题为空，使用原始文件名 '{document['original_filename']}' 作为标题")
                else:
                    # 如果原始文件名也为空，使用默认标题
                    document['title'] = f"无标题文档 #{document['id']}"
                    logging.info(f"文档ID {document['id']}: 标题和原始文件名均为空，使用默认标题 '{document['title']}'")
            else:
                logging.info(f"文档ID {document['id']}: 使用原始标题 '{document['title']}'")
            
            # 尝试获取HTML内容
            cursor.execute('''
            SELECT html_content 
            FROM document_html_content 
            WHERE doc_id = ?
            ''', (document['id'],))
            
            html_row = cursor.fetchone()
            
            if html_row and html_row['html_content']:
                document['html_content'] = html_row['html_content']
            
            return document
            
        except Exception as e:
            logging.error(f"获取文档失败: {e}")
            return None
        finally:
            if conn:
                conn.close() 