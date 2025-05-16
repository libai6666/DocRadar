"""
搜索引擎模块
基于SQLite FTS5实现全文搜索功能
"""
import sqlite3
import logging
import re
import os
from config import DATABASE, PREVIEW_LENGTH, SEARCH_RESULT_LIMIT

class SearchEngine:
    """基于SQLite FTS5的搜索引擎"""
    
    def __init__(self, db_path=DATABASE):
        """
        初始化搜索引擎
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        """初始化数据库和FTS5表"""
        try:
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
                metadata TEXT
            )
            ''')
            
            # 检查是否需要重建FTS5表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_content'")
            fts_exists = cursor.fetchone() is not None
            
            if fts_exists:
                # 检查当前FTS表的配置
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='document_content'")
                fts_config = cursor.fetchone()[0].lower()
                
                # 如果需要更新配置 (在这里我们不再检查trigram，而是使用更通用的条件)
                if 'unicode61' not in fts_config:
                    logging.info("正在重建FTS5表以支持更好的模糊搜索...")
                    
                    # 保存现有数据
                    cursor.execute("SELECT doc_id, content FROM document_content")
                    existing_docs = cursor.fetchall()
                    
                    # 删除旧表
                    cursor.execute("DROP TABLE IF EXISTS document_content")
                    
                    # 创建新表，使用有效的分词器选项
                    cursor.execute('''
                    CREATE VIRTUAL TABLE document_content USING fts5(
                        doc_id UNINDEXED,
                        content,
                        tokenize='porter unicode61'
                    )
                    ''')
                    
                    # 恢复数据
                    for doc_id, content in existing_docs:
                        cursor.execute(
                            "INSERT INTO document_content (doc_id, content) VALUES (?, ?)",
                            (doc_id, content)
                        )
                    
                    logging.info(f"已重建FTS5表并恢复 {len(existing_docs)} 个文档")
            else:
                # 创建新的文档内容FTS5表，使用有效的分词器
                cursor.execute('''
                CREATE VIRTUAL TABLE document_content USING fts5(
                    doc_id UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                )
                ''')
            
            conn.commit()
            conn.close()
            logging.info("Database initialized successfully with enhanced search capabilities")
            
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def add_document(self, doc_id, content, conn=None):
        """
        添加文档内容到搜索索引
        
        Args:
            doc_id: 文档ID
            content: 文档内容文本
            conn: 数据库连接（可选）
        """
        should_close = False
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            should_close = True
            
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO document_content (doc_id, content) VALUES (?, ?)",
                (doc_id, content)
            )
            
            if should_close:
                conn.commit()
                conn.close()
                
            logging.info(f"Document {doc_id} added to search index")
            
        except sqlite3.Error as e:
            logging.error(f"Error adding document to search index: {e}")
            if should_close:
                conn.rollback()
                conn.close()
            raise
    
    def search(self, query, limit=SEARCH_RESULT_LIMIT):
        """
        搜索文档内容，支持模糊匹配
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            list: 搜索结果列表
        """
        results = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 尝试使用FTS5查询
            try:
                search_query = query
                logging.info(f"尝试使用FTS5执行搜索: {search_query}")
                
                cursor.execute('''
                SELECT 
                    d.id, 
                    d.filename, 
                    d.filepath, 
                    d.title, 
                    d.file_type,
                    d.file_size,
                    d.created_at,
                    c.content,
                    snippet(document_content, 0, '<mark>', '</mark>', '...', 10) as snippet
                FROM 
                    document_content c
                JOIN 
                    documents d ON c.doc_id = d.id
                WHERE 
                    document_content MATCH ?
                ORDER BY 
                    rank
                LIMIT ?
                ''', (search_query, limit))
                
                rows = cursor.fetchall()
                if rows:
                    # FTS5查询成功且有结果
                    for row in rows:
                        content = row['content']
                        preview = self._generate_preview(content, query, PREVIEW_LENGTH)
                        
                        result = {
                            'id': row['id'],
                            'filename': row['filename'],
                            'filepath': row['filepath'],
                            'title': row['title'] or row['filename'],
                            'file_type': row['file_type'],
                            'file_size': row['file_size'],
                            'created_at': row['created_at'],
                            'preview': preview,
                            'snippet': row['snippet']
                        }
                        results.append(result)
                    
                    logging.info(f"FTS5查询成功，找到 {len(results)} 个匹配结果")
                    return results
                else:
                    # FTS5没有找到结果，使用备用查询
                    logging.info("FTS5查询没有找到结果，使用备用查询")
                    raise sqlite3.OperationalError("No results found with FTS5, using fallback")
                    
            except sqlite3.OperationalError as e:
                logging.warning(f"FTS5查询失败或无结果，使用备用查询方法: {e}")
                
            # 备用方法：使用LIKE查询进行模糊匹配
            query_terms = query.strip().split()
            if not query_terms:
                return []
            
            # 构建LIKE条件
            like_conditions = []
            params = []
            
            # 从所有文档中提取数据
            cursor.execute('''
            SELECT 
                id, 
                filename, 
                filepath, 
                title, 
                file_type,
                file_size,
                created_at
            FROM 
                documents
            ORDER BY 
                created_at DESC
            LIMIT ?
            ''', (limit * 3,))  # 获取更多结果用于过滤
            
            rows = cursor.fetchall()
            potential_results = []
            
            for row in rows:
                # 从文件直接获取内容
                doc_content = None
                try:
                    filepath = row['filepath']
                    
                    if os.path.exists(filepath):
                        # 解析文件内容
                        from utils.document_parser import DocumentParser
                        parser = DocumentParser.get_parser(filepath)
                        parsed_content = parser.parse(filepath)
                        
                        doc_content = parsed_content['text']
                except Exception as file_error:
                    logging.error(f"从文件获取内容失败: {file_error}")
                
                # 如果无法获取内容，跳过此文档
                if not doc_content:
                    continue
                
                # 检查是否包含所有查询词（模糊匹配）
                match_score = 0
                content_lower = doc_content.lower()
                
                for term in query_terms:
                    term_lower = term.lower()
                    if term_lower in content_lower:
                        match_score += 1
                
                # 如果至少匹配一个词，添加到结果中，并记录匹配分数
                if match_score > 0:
                    preview = self._generate_preview(doc_content, query, PREVIEW_LENGTH)
                    
                    result = {
                        'id': row['id'],
                        'filename': row['filename'],
                        'filepath': row['filepath'],
                        'title': row['title'] or row['filename'],
                        'file_type': row['file_type'],
                        'file_size': row['file_size'],
                        'created_at': row['created_at'],
                        'preview': preview,
                        'content': doc_content,  # 用于生成snippet
                        'match_score': match_score  # 匹配分数用于排序
                    }
                    potential_results.append(result)
            
            # 按匹配分数排序（从高到低）
            potential_results.sort(key=lambda x: x['match_score'], reverse=True)
            
            # 限制结果数量
            results = potential_results[:limit]
            
            # 生成snippet并移除content字段
            for result in results:
                # 尝试生成一个简单的snippet
                snippets = []
                content_lower = result['content'].lower()
                
                for term in query_terms:
                    term_lower = term.lower()
                    
                    # 查找每个词的位置
                    pos = content_lower.find(term_lower)
                    if pos >= 0:
                        # 获取上下文（前后30个字符）
                        context_start = max(0, pos - 30)
                        context_end = min(len(content_lower), pos + len(term_lower) + 30)
                        
                        # 获取原始大小写的上下文
                        context = result['content'][context_start:context_end]
                        
                        # 在上下文中标记匹配词
                        original_term = result['content'][pos:pos+len(term_lower)]
                        marked_context = context.replace(original_term, f'<mark>{original_term}</mark>')
                        snippets.append(f"...{marked_context}...")
                
                # 只保留最多3个片段
                if snippets:
                    result['snippet'] = ' '.join(snippets[:3])
                else:
                    result['snippet'] = ""
                
                # 删除不需要的字段
                if 'content' in result:
                    del result['content']
                if 'match_score' in result:
                    del result['match_score']
            
            logging.info(f"备用查询找到 {len(results)} 个模糊匹配结果")
            
            conn.close()
            
        except sqlite3.Error as e:
            logging.error(f"Search error: {e}")
            raise
            
        return results
    
    def _generate_preview(self, content, query, length=200):
        """生成预览文本，包含模糊匹配的搜索词上下文"""
        if not query or not content:
            return content[:length] + "..." if len(content) > length else content
        
        # 分割查询词
        query_terms = query.split()
        best_pos = -1
        best_term = ""
        
        content_lower = content.lower()
        
        # 查找第一个匹配的词（模糊匹配）
        for term in query_terms:
            term_lower = term.lower()
            pos = content_lower.find(term_lower)
            if pos >= 0 and (best_pos == -1 or pos < best_pos):
                best_pos = pos
                best_term = term
        
        # 如果找不到任何匹配，返回内容的开头部分
        if best_pos == -1:
            return content[:length] + "..." if len(content) > length else content
        
        # 计算预览的起始和结束位置
        half_length = length // 2
        start = max(0, best_pos - half_length)
        end = min(len(content), best_pos + half_length)
        
        # 调整以避免在单词中间截断
        if start > 0:
            # 找到前一个空格
            prev_space = content.rfind(' ', 0, start)
            if prev_space != -1:
                start = prev_space + 1
        
        if end < len(content):
            # 找到下一个空格
            next_space = content.find(' ', end)
            if next_space != -1:
                end = next_space
        
        # 生成预览文本
        preview = content[start:end]
        if start > 0:
            preview = "..." + preview
        if end < len(content):
            preview = preview + "..."
            
        return preview
    
    def get_document_by_id(self, doc_id):
        """
        根据ID获取文档内容
        
        Args:
            doc_id: 文档ID
            
        Returns:
            dict: 文档信息和内容
        """
        document = None
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 尝试使用FTS5查询（联合documents和document_content表）
            try:
                cursor.execute('''
                SELECT 
                    d.*, 
                    c.content
                FROM 
                    documents d
                JOIN 
                    document_content c ON d.id = c.doc_id
                WHERE 
                    d.id = ?
                ''', (doc_id,))
                
                row = cursor.fetchone()
                if row:
                    document = {
                        'id': row['id'],
                        'filename': row['filename'],
                        'filepath': row['filepath'],
                        'title': row['title'] or row['filename'],
                        'file_type': row['file_type'],
                        'file_size': row['file_size'],
                        'created_at': row['created_at'],
                        'content': row['content']
                    }
            except sqlite3.OperationalError as e:
                # FTS5模块不可用或查询失败
                logging.error(f"FTS5查询失败: {e}")
                
            # 如果FTS5查询失败或没有结果，尝试仅从documents表获取基本信息
            if not document:
                logging.info(f"尝试使用备用查询获取文档 {doc_id} 的基本信息")
                cursor.execute('''
                SELECT 
                    id, filename, filepath, title, file_type, file_size, created_at, metadata
                FROM 
                    documents
                WHERE 
                    id = ?
                ''', (doc_id,))
                
                row = cursor.fetchone()
                if row:
                    # 获取基本文档信息
                    document = {
                        'id': row['id'],
                        'filename': row['filename'],
                        'filepath': row['filepath'],
                        'title': row['title'] or row['filename'],
                        'file_type': row['file_type'],
                        'file_size': row['file_size'],
                        'created_at': row['created_at'],
                        'content': "无法加载文档内容。可能是因为搜索引擎模块(FTS5)不可用。"
                    }
                    
                    # 尝试直接从文件读取内容
                    if os.path.exists(row['filepath']):
                        try:
                            logging.info(f"尝试直接从文件读取内容: {row['filepath']}")
                            
                            # 根据文件类型选择解析方法
                            from utils.document_parser import DocumentParser
                            parser = DocumentParser.get_parser(row['filepath'])
                            doc_content = parser.parse(row['filepath'])
                            
                            document['content'] = doc_content['text']
                            if 'html_content' in doc_content:
                                document['html_content'] = doc_content['html_content']
                                
                            logging.info(f"成功从文件直接解析内容: {row['filepath']}")
                        except Exception as file_error:
                            logging.error(f"从文件解析内容失败: {file_error}")
            
            # 如果是DOCX文件且内容存在，但html_content不存在，尝试重新解析获取HTML内容
            if document and document['file_type'] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' and os.path.exists(document['filepath']) and 'html_content' not in document:
                try:
                    from utils.document_parser import DocxParser
                    parser = DocxParser()
                    doc_content = parser.parse(document['filepath'])
                    if 'html_content' in doc_content:
                        document['html_content'] = doc_content['html_content']
                except Exception as e:
                    logging.warning(f"重新解析DOCX文件失败: {e}")
            
            conn.close()
            
            if document:
                logging.info(f"成功获取文档: {doc_id}, 标题: {document['title']}")
            else:
                logging.warning(f"文档不存在: {doc_id}")
                
            return document
            
        except sqlite3.Error as e:
            logging.error(f"Error retrieving document: {e}")
            raise
    
    def highlight_content(self, content, query):
        """
        在内容中高亮显示查询词，支持模糊匹配
        
        Args:
            content: 文档内容
            query: 搜索查询
            
        Returns:
            str: 高亮后的HTML内容
        """
        if not query or not content:
            # 将换行符转换为HTML换行并返回
            return content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>\n')
        
        # 获取查询词
        terms = query.split()
        
        # 对内容进行HTML转义
        escaped_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 存储需要高亮的区间
        highlight_ranges = []
        
        content_lower = escaped_content.lower()
        
        # 对每个查询词进行模糊匹配
        for term in terms:
            if not term or len(term) < 2:  # 忽略太短的词
                continue
                
            term_lower = term.lower()
            
            # 查找所有匹配位置
            start_pos = 0
            while start_pos < len(content_lower):
                pos = content_lower.find(term_lower, start_pos)
                if pos == -1:
                    break
                    
                highlight_ranges.append((pos, pos + len(term_lower)))
                start_pos = pos + 1  # 从下一个位置继续查找，允许重叠匹配
        
        # 按照起始位置排序
        highlight_ranges.sort()
        
        # 合并重叠区间
        if highlight_ranges:
            merged_ranges = [highlight_ranges[0]]
            for current in highlight_ranges[1:]:
                prev = merged_ranges[-1]
                # 如果当前区间与前一个重叠，则合并
                if current[0] <= prev[1]:
                    merged_ranges[-1] = (prev[0], max(prev[1], current[1]))
                else:
                    merged_ranges.append(current)
            highlight_ranges = merged_ranges
        
        # 从后往前插入高亮标记（避免位置偏移）
        result = escaped_content
        for start, end in sorted(highlight_ranges, key=lambda x: x[1], reverse=True):
            matched_text = result[start:end]
            result = result[:start] + f'<mark>{matched_text}</mark>' + result[end:]
        
        # 将换行符转换为HTML换行
        result = result.replace('\n', '<br>\n')
        
        logging.info(f"高亮搜索词 '{query}' 找到 {len(highlight_ranges)} 个匹配")
        
        return result 