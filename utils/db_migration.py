"""
数据库迁移脚本
用于更新数据库结构
"""
import sqlite3
import logging
from config import DATABASE

def migrate_db():
    """执行数据库迁移"""
    logging.info("开始执行数据库迁移...")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # 检查original_filename列是否已存在
        cursor.execute("PRAGMA table_info(documents)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # 如果original_filename列不存在，添加它
        if 'original_filename' not in column_names:
            logging.info("添加original_filename列到documents表")
            cursor.execute("ALTER TABLE documents ADD COLUMN original_filename TEXT")
            
            # 初始化新列的值为当前filename的值
            cursor.execute("UPDATE documents SET original_filename = filename")
            
            conn.commit()
            logging.info("成功添加original_filename列到documents表")
        else:
            logging.info("original_filename列已存在，无需迁移")
        
    except Exception as e:
        conn.rollback()
        logging.error(f"数据库迁移失败: {e}")
        raise
    finally:
        conn.close()
    
    logging.info("数据库迁移完成")

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    migrate_db() 