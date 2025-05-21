"""
数据库初始化脚本 - 使用标准SQL表
创建必要的数据库表
"""
import sqlite3
import os
from config import DATABASE

def init_db():
    """初始化数据库，创建必要的表 - 使用标准SQL表替代FTS5"""
    # 确保数据库目录存在
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建文档元数据表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        title TEXT,
        file_type TEXT,
        file_size INTEGER,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        original_filename TEXT
    )
    ''')
    
    # 创建文档内容表（标准表代替FTS5）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS document_content (
        doc_id INTEGER PRIMARY KEY,
        content TEXT,
        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
    )
    ''')
    
    # 创建HTML内容表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS document_html_content (
        doc_id INTEGER PRIMARY KEY,
        html_content TEXT,
        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
    )
    ''')
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print("数据库初始化完成！使用标准SQL表代替FTS5。")

if __name__ == '__main__':
    init_db() 