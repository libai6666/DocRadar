#!/usr/bin/env python
"""
提取已有文档的日期脚本
用于更新现有文档记录，从文档内容中提取日期信息
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import DATABASE_URI, ENV
from app.utils.document_parser import DocumentParser

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'extract_dates_{ENV}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

def extract_dates_for_existing_documents():
    """为现有文档提取日期"""
    setup_logging()
    
    logging.info(f"开始为现有文档提取日期 - 环境: {ENV}")
    logging.info(f"数据库路径: {DATABASE_URI}")
    
    try:
        conn = sqlite3.connect(DATABASE_URI)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询所有没有document_date的文档
        cursor.execute("""
            SELECT id, filepath, file_type, title, original_filename 
            FROM documents 
            WHERE document_date IS NULL OR document_date = ''
        """)
        
        documents = cursor.fetchall()
        total_docs = len(documents)
        
        logging.info(f"找到 {total_docs} 个需要提取日期的文档")
        
        if total_docs == 0:
            logging.info("没有需要处理的文档")
            return
        
        updated_count = 0
        error_count = 0
        
        for i, doc in enumerate(documents, 1):
            doc_id = doc['id']
            filepath = doc['filepath']
            file_type = doc['file_type']
            title = doc['title']
            original_filename = doc['original_filename']
            
            logging.info(f"处理文档 {i}/{total_docs}: {title} (ID: {doc_id})")
            
            try:
                # 检查文件是否存在
                if not os.path.exists(filepath):
                    logging.warning(f"文件不存在: {filepath}")
                    continue
                
                # 获取合适的解析器
                parser = DocumentParser.get_parser(filepath)
                
                # 解析文档以提取文本内容
                parse_result = parser.parse(filepath, doc_id)
                text_content = parse_result.get('text', '')
                
                if not text_content:
                    logging.warning(f"无法从文档中提取文本内容: {filepath}")
                    continue
                
                # 提取日期
                document_date = parser.extract_document_date(text_content)
                
                if document_date:
                    # 更新数据库
                    cursor.execute("""
                        UPDATE documents 
                        SET document_date = ? 
                        WHERE id = ?
                    """, (document_date, doc_id))
                    
                    logging.info(f"成功提取并更新文档日期: {document_date} (文档: {title})")
                    updated_count += 1
                else:
                    logging.info(f"未能从文档中提取到日期: {title}")
                
            except Exception as e:
                logging.error(f"处理文档失败 {title} (ID: {doc_id}): {e}")
                error_count += 1
                continue
        
        # 提交更改
        conn.commit()
        
        logging.info(f"处理完成:")
        logging.info(f"  总文档数: {total_docs}")
        logging.info(f"  成功更新: {updated_count}")
        logging.info(f"  错误数量: {error_count}")
        logging.info(f"  跳过数量: {total_docs - updated_count - error_count}")
        
    except Exception as e:
        logging.error(f"提取日期过程中出现错误: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    extract_dates_for_existing_documents()

