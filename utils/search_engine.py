"""
搜索引擎模块
使用常规SQL查询实现全文搜索功能
"""
import sqlite3
import logging
import re
import os
from config import DATABASE, PREVIEW_LENGTH, SEARCH_RESULT_LIMIT

class SearchEngine:
    """基于SQL LIKE的搜索引擎"""
    
    def __init__(self, db_path=DATABASE):
        """
        初始化搜索引擎
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        """初始化数据库和文档内容表"""
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
            
            # 创建文档内容表（不使用FTS5）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_content (
                doc_id INTEGER PRIMARY KEY,
                content TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("数据库初始化完成，使用基础SQL查询功能")
            
        except sqlite3.Error as e:
            logging.error(f"数据库初始化错误: {e}")
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
            
            # 检查是否已存在该文档的内容
            cursor.execute("SELECT doc_id FROM document_content WHERE doc_id = ?", (doc_id,))
            exists = cursor.fetchone()
            
            if exists:
                # 更新现有内容
                cursor.execute(
                    "UPDATE document_content SET content = ? WHERE doc_id = ?",
                    (content, doc_id)
                )
            else:
                # 插入新内容
                cursor.execute(
                    "INSERT INTO document_content (doc_id, content) VALUES (?, ?)",
                    (doc_id, content)
                )
            
            if should_close:
                conn.commit()
                conn.close()
                
            logging.info(f"文档 {doc_id} 已添加到搜索索引")
            
        except sqlite3.Error as e:
            logging.error(f"添加文档到搜索索引失败: {e}")
            if should_close:
                conn.rollback()
                conn.close()
            raise
    
    def search(self, query, limit=SEARCH_RESULT_LIMIT):
        """
        搜索文档内容，使用LIKE实现模糊匹配
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            list: 搜索结果列表
        """
        results = []
        
        try:
            # 准备搜索关键词
            keywords = [kw.strip() for kw in query.split() if kw.strip()]
            if not keywords:
                return []
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有文档
            cursor.execute('''
            SELECT 
                d.id, 
                d.filename, 
                d.filepath, 
                d.title, 
                d.file_type,
                d.file_size,
                d.created_at,
                c.content
            FROM 
                documents d
            LEFT JOIN
                document_content c ON d.id = c.doc_id
            ORDER BY 
                d.created_at DESC
            LIMIT ?
            ''', (limit * 3,))  # 获取更多结果用于过滤
            
            rows = cursor.fetchall()
            
            for row in rows:
                doc_id = row['id']
                content = row['content']
                
                # 如果数据库中没有内容，尝试从文件直接读取
                if not content:
                    try:
                        filepath = row['filepath']
                        if os.path.exists(filepath):
                            # 解析文件内容
                            from utils.document_parser import DocumentParser
                            parser = DocumentParser.get_parser(filepath)
                            parsed_content = parser.parse(filepath)
                            content = parsed_content['text']
                    except Exception as e:
                        logging.error(f"解析文件内容失败: {e}")
                        continue
                
                if not content:
                    continue
                    
                # 检查内容是否包含所有关键词（模糊匹配）
                content_lower = content.lower()
                match_positions = []
                
                # 检查每个关键词
                all_keywords_found = True
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower not in content_lower:
                        all_keywords_found = False
                        break
                        
                    # 记录所有匹配位置
                    start = 0
                    while True:
                        pos = content_lower.find(keyword_lower, start)
                        if pos == -1:
                            break
                        match_positions.append((pos, len(keyword)))
                        start = pos + 1
                
                if not all_keywords_found:
                    continue
                    
                # 为匹配结果生成预览和片段
                preview = self._generate_preview(content, query, PREVIEW_LENGTH)
                snippet = self._generate_snippet(content, query)
                
                result = {
                    'id': row['id'],
                    'filename': row['filename'],
                    'filepath': row['filepath'],
                    'title': row['title'] or row['filename'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size'],
                    'created_at': row['created_at'],
                    'preview': preview,
                    'snippet': snippet,
                    'match_count': len(match_positions)
                }
                results.append(result)
                
                # 如果已经找到足够的结果，就停止
                if len(results) >= limit:
                    break
                    
            conn.close()
            return results
            
        except sqlite3.Error as e:
            logging.error(f"搜索失败: {e}")
            raise
    
    def _generate_snippet(self, content, query, max_snippets=3, snippet_length=100):
        """生成带高亮标记的文本片段"""
        if not query or not content:
            return content[:snippet_length] + "..." if len(content) > snippet_length else content
        
        # 分割查询词
        query_terms = query.split()
        snippets = []
        content_lower = content.lower()
        
        # 查找每个查询词的匹配位置
        for term in query_terms:
            if not term or len(term) < 2:  # 忽略太短的词
                continue
                
            term_lower = term.lower()
            start_pos = 0
            
            while len(snippets) < max_snippets:
                pos = content_lower.find(term_lower, start_pos)
                if pos == -1:
                    break
                    
                # 计算片段的起始和结束位置
                half_length = snippet_length // 2
                start = max(0, pos - half_length)
                end = min(len(content), pos + len(term_lower) + half_length)
                
                # 调整以避免在单词中间截断
                if start > 0:
                    prev_space = content.rfind(' ', 0, start)
                    if prev_space != -1:
                        start = prev_space + 1
                
                if end < len(content):
                    next_space = content.find(' ', end)
                    if next_space != -1:
                        end = next_space
                
                # 提取片段并添加...表示省略
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                    
                # 对片段中的查询词进行高亮
                for search_term in query_terms:
                    if len(search_term) < 2:
                        continue
                    term_regex = re.compile(re.escape(search_term), re.IGNORECASE)
                    snippet = term_regex.sub(f'<mark>\\g<0></mark>', snippet)
                
                snippets.append(snippet)
                start_pos = pos + 1  # 从下一个位置继续查找
        
        # 如果没有找到任何片段，使用文档开头作为片段
        if not snippets:
            snippet = content[:snippet_length] + "..." if len(content) > snippet_length else content
            snippets.append(snippet)
        
        # 将所有片段连接起来
        return " [...] ".join(snippets)
    
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
            
            # 从文档和内容表中获取数据
            cursor.execute('''
            SELECT 
                d.*, 
                c.content
            FROM 
                documents d
            LEFT JOIN 
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
                    'content': row['content'] or ""
                }
                
                # 如果内容为空，尝试从文件直接读取
                if not document['content'] and os.path.exists(row['filepath']):
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
                        document['content'] = "无法加载文档内容。可能是因为文件格式不支持或文件已损坏。"
            
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
            logging.error(f"获取文档失败: {e}")
            raise
    
    def highlight_content(self, content, query):
        """
        在内容中高亮显示所有查询词，支持模糊匹配
        
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
            result = result[:start] + f'<mark data-match="true">{matched_text}</mark>' + result[end:]
        
        # 将换行符转换为HTML换行
        result = result.replace('\n', '<br>\n')
        
        logging.info(f"高亮搜索词 '{query}' 找到 {len(highlight_ranges)} 个匹配")
        
        return result 