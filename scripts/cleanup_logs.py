"""
日志清理脚本
自动删除超过7天的日志文件
"""
import os
import glob
import time
from datetime import datetime, timedelta
import logging

# 配置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cleanup_logs(log_dir, days_to_keep=7):
    """
    清理指定目录中超过指定天数的日志文件
    
    Args:
        log_dir: 日志目录路径
        days_to_keep: 保留的天数，默认7天
    """
    if not os.path.exists(log_dir):
        logging.warning(f"日志目录不存在: {log_dir}")
        return
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_timestamp = cutoff_date.timestamp()
    
    # 获取匹配模式的所有日志文件
    log_pattern = os.path.join(log_dir, "*.log*")
    deleted_count = 0
    error_count = 0
    
    for log_file in glob.glob(log_pattern):
        try:
            # 获取文件修改时间
            file_mtime = os.path.getmtime(log_file)
            
            # 如果文件修改时间早于截止日期，则删除
            if file_mtime < cutoff_timestamp:
                try:
                    os.remove(log_file)
                    logging.info(f"已删除旧日志文件: {log_file}")
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"无法删除日志文件 {log_file}: {e}")
                    error_count += 1
        except Exception as e:
            logging.error(f"处理日志文件 {log_file} 时出错: {e}")
            error_count += 1
    
    logging.info(f"日志清理完成。删除了 {deleted_count} 个文件，失败 {error_count} 个。")
    return deleted_count, error_count

if __name__ == "__main__":
    # 项目根目录
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # 清理测试环境日志
    test_log_dir = os.path.join(ROOT_DIR, 'logs', 'test')
    logging.info(f"开始清理测试环境日志: {test_log_dir}")
    cleanup_logs(test_log_dir)
    
    # 清理生产环境日志
    prod_log_dir = os.path.join(ROOT_DIR, 'logs', 'production')
    logging.info(f"开始清理生产环境日志: {prod_log_dir}")
    cleanup_logs(prod_log_dir) 