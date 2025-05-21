#!/usr/bin/env python
"""
数据库文件迁移脚本
确保数据库文件在正确位置，并在新旧路径之间复制如果需要
"""

import os
import sys
import logging
import shutil

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

# 数据目录路径
DATA_DIR = os.path.join(ROOT_DIR, 'data')

# 测试环境路径
TEST_DB_DIR = os.path.join(DATA_DIR, 'test', 'db')
TEST_DB_FILE = os.path.join(TEST_DB_DIR, 'docradar_test.db')

# 生产环境路径
PROD_DB_DIR = os.path.join(DATA_DIR, 'production', 'db')
PROD_DB_FILE = os.path.join(PROD_DB_DIR, 'docradar_prod.db')

# 旧的数据库文件路径
OLD_DB_FILE = os.path.join(ROOT_DIR, 'docradar.db')

def ensure_dir(dir_path):
    """确保目录存在"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        logging.info(f"创建目录: {dir_path}")
    return dir_path

def copy_if_newer(src, dst):
    """如果源文件较新或目标不存在，则复制文件"""
    if not os.path.exists(src):
        logging.info(f"源文件不存在，跳过复制: {src}")
        return False
    
    if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
        ensure_dir(os.path.dirname(dst))
        shutil.copy2(src, dst)
        logging.info(f"复制文件: {src} -> {dst}")
        return True
    
    logging.info(f"目标文件已是最新，无需复制: {dst}")
    return False

def migrate_db_files():
    """迁移数据库文件"""
    # 确保目录存在
    ensure_dir(TEST_DB_DIR)
    ensure_dir(PROD_DB_DIR)
    
    # 检查旧的数据库文件
    if os.path.exists(OLD_DB_FILE):
        logging.info(f"发现旧的数据库文件: {OLD_DB_FILE}")
        
        # 复制到测试环境
        copy_if_newer(OLD_DB_FILE, TEST_DB_FILE)
        
        # 复制到生产环境
        copy_if_newer(OLD_DB_FILE, PROD_DB_FILE)
    else:
        logging.info(f"未找到旧的数据库文件: {OLD_DB_FILE}")

if __name__ == "__main__":
    logging.info("开始数据库文件迁移...")
    migrate_db_files()
    logging.info("数据库文件迁移完成") 