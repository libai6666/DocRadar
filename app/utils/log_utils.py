"""
日志工具模块
提供带用户上下文的日志记录功能
"""
import logging
import threading
from flask import session, g, has_request_context
from datetime import datetime, timezone, timedelta

# 使用线程本地存储来保存当前请求的用户名
_thread_local = threading.local()

class UsernameFormatter(logging.Formatter):
    """自定义日志格式化器，添加用户名字段并使用北京时间"""
    
    def formatTime(self, record, datefmt=None):
        """
        重写格式化时间方法，使用北京时间
        
        Args:
            record: 日志记录
            datefmt: 日期格式
            
        Returns:
            str: 格式化的北京时间字符串
        """
        # 获取UTC时间
        utc_time = datetime.fromtimestamp(record.created, timezone.utc)
        
        # 转换为北京时间（UTC+8）
        beijing_tz = timezone(timedelta(hours=8))
        beijing_time = utc_time.astimezone(beijing_tz)
        
        # 使用指定格式或默认格式
        if datefmt:
            return beijing_time.strftime(datefmt)
        else:
            return beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    
    def formatMessage(self, record):
        """
        格式化日志消息，确保 username 字段存在
        
        Args:
            record: 日志记录对象
            
        Returns:
            str: 格式化的日志消息
        """
        # 如果记录中没有 username 字段，添加默认值
        if not hasattr(record, 'username'):
            # 首先尝试从线程本地存储获取用户名
            username = getattr(_thread_local, 'username', None)
            
            # 如果线程本地存储中没有，尝试从 Flask 上下文获取
            if username is None:
                try:
                    if has_request_context():
                        username = g.get('username', '未登录')
                    else:
                        username = '系统'
                except Exception:
                    username = '系统'
            
            # 设置记录的用户名
            record.username = username
                
        # 调用父类的格式化方法
        return super().formatMessage(record)

def get_current_username():
    """
    获取当前用户名并存储到线程本地变量
    
    Returns:
        str: 当前用户名，如果没有则返回"未登录"或"系统"
    """
    if has_request_context():
        username = session.get('user', '未登录')
        # 存储到线程本地变量，供所有日志记录器使用
        _thread_local.username = username
        return username
    return "系统" 