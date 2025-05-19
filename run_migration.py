"""
运行数据库迁移脚本
"""
import logging
from utils.db_migration import migrate_db

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 执行迁移
    migrate_db()
    
    print("数据库迁移已完成。") 