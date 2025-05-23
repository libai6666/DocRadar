"""
DocRadar应用初始化模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, g, send_from_directory
from datetime import datetime, timezone, timedelta
import glob
import time
import sys
from flask_cors import CORS
from flask import Blueprint, redirect, url_for
from app.core.config import (
    ENV, HOST, PORT, SECRET_KEY, LOG_DIR, LOG_LEVEL, LOG_FILE,
    DOCUMENT_IMAGES_DIR, DOCUMENT_IMAGES_URL
)

# 尝试导入CSRF保护
try:
    from flask_wtf.csrf import CSRFProtect
    has_csrf = True
    print("已启用CSRF保护")
except ImportError:
    has_csrf = False
    print("警告: flask-wtf模块未安装，CSRF保护将不可用")
    print("提示: 可以通过运行 'pip install Flask-WTF==1.0.0' 来安装此模块")

from app.core.config import SECRET_KEY, LOG_DIR, LOG_LEVEL, LOG_FILE
from app.core.routes import main_bp
from app.core.document_routes import document_bp, compat_bp
from app.core.search_routes import search_bp
from app.core.admin_routes import admin_bp

# 定义应用级别变量来跟踪日志状态
_last_log_date = None
_log_updated_today = False

def create_app(test_config=None):
    """创建并配置Flask应用实例"""
    # 创建Flask应用
    app = Flask(__name__, 
                static_url_path="/static",
                static_folder="static",
                template_folder="templates")
    
    # 设置应用配置
    app.config.from_mapping(
        SECRET_KEY=SECRET_KEY,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 最大上传文件大小（50MB）
        SESSION_TYPE='filesystem',  # 使用文件系统存储session
        SESSION_PERMANENT=True,     # 持久化session
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),  # session有效期
        DEBUG=True  # 开启调试模式
    )
    
    # 初始化CSRF保护
    if has_csrf:
        csrf = CSRFProtect(app)
        logging.info("CSRF保护已启用")
        
        # 为兼容性路由添加CSRF豁免
        csrf.exempt('compat.compat_check_file_exists_get')
        csrf.exempt('compat.compat_batch_upload')
        logging.info("已为兼容性路由添加CSRF豁免")
    
    # 尝试初始化会话扩展
    try:
        from flask_session import Session
        Session(app)
        logging.info("使用Flask-Session进行会话管理")
    except ImportError:
        logging.warning("Flask-Session未安装，使用默认会话管理")
        print("提示: 可以通过运行 'pip install Flask-Session==0.4.0' 来安装此模块")
    
    # 创建文档图片目录的符号链接，确保可以通过web访问
    static_doc_images_dir = os.path.join(app.static_folder, 'document_images')
    
    # 确保静态目录存在，但不再用于存储实际图片
    if not os.path.exists(static_doc_images_dir):
        os.makedirs(static_doc_images_dir, exist_ok=True)
    
    # 确保占位符图片存在
    placeholder_dir = os.path.join(app.static_folder, 'images')
    if not os.path.exists(placeholder_dir):
        os.makedirs(placeholder_dir, exist_ok=True)
    
    # 确保文档图片目录存在
    docs_dir = os.path.join(placeholder_dir, 'docs')
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir, exist_ok=True)
        logging.info(f"创建文档图片目录: {docs_dir}")
    
    placeholder_path = os.path.join(placeholder_dir, 'image_placeholder.png')
    if not os.path.exists(placeholder_path):
        # 创建一个简单的占位符图片
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (200, 150), color=(240, 240, 240))
            d = ImageDraw.Draw(img)
            d.text((40, 65), "图片加载失败", fill=(80, 80, 80))
            img.save(placeholder_path)
            logging.info(f"创建占位符图片: {placeholder_path}")
        except Exception as e:
            logging.warning(f"创建占位符图片失败: {e}")
            # 如果无法创建图片，尝试写入一个空文件
            with open(placeholder_path, 'wb') as f:
                f.write(b'')
    
    # 添加beijing_time过滤器
    @app.template_filter('beijing_time')
    def beijing_time_filter(timestamp):
        """转换时间戳为北京时间（UTC+8）并格式化
        
        Args:
            timestamp: 时间戳字符串或datetime对象
            
        Returns:
            str: 格式化的北京时间字符串
        """
        if not timestamp:
            return ""
        
        # 如果输入是字符串，尝试转换为datetime对象
        if isinstance(timestamp, str):
            try:
                # 尝试各种常见的时间格式
                formats = [
                    '%Y-%m-%d %H:%M:%S',  # 标准格式
                    '%Y-%m-%d %H:%M:%S.%f',  # 带微秒
                    '%Y-%m-%dT%H:%M:%S',  # ISO格式
                    '%Y-%m-%dT%H:%M:%S.%f',  # ISO格式带微秒
                    '%Y-%m-%d'  # 仅日期
                ]
                
                for fmt in formats:
                    try:
                        timestamp = datetime.strptime(timestamp, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # 如果所有格式都不匹配
                    return timestamp  # 返回原始字符串
            except Exception:
                return timestamp  # 转换失败时返回原始字符串
        
        # 如果不是datetime对象，返回原始值
        if not isinstance(timestamp, datetime):
            return timestamp
        
        # 如果datetime对象没有时区信息，假定为UTC
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        # 转换为北京时间 (UTC+8)
        beijing_tz = timezone(timedelta(hours=8))
        beijing_time = timestamp.astimezone(beijing_tz)
        
        # 格式化为易读格式
        return beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 配置日志
    _setup_logging()
    
    # 在每个请求之前检查日志文件日期
    @app.before_request
    def check_log_file_date():
        global _last_log_date, _log_updated_today
        
        # 获取当前日期
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 仅在日期变化或首次运行时更新日志文件
        if _last_log_date != today:
            _last_log_date = today
            _log_updated_today = False
            
        # 确保每天只输出一次日志更新消息
        if not _log_updated_today:
            _update_log_file_handler(today)
            _log_updated_today = True
        
        # 在请求对象中存储当前日志日期
        g.log_date = today
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(compat_bp)  # 注册兼容性路由蓝图
    
    # 启用CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # 根路由重定向到首页
    @app.route('/')
    def index():
        return redirect(url_for('core.home'))
    
    # 错误处理
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404
    
    @app.errorhandler(500)
    def server_error(e):
        logging.error(f"服务器错误: {e}")
        return render_template("500.html"), 500
    
    # 为文档图片创建直接访问路由
    @app.route('/document_images/<path:image_path>')
    def serve_document_image(image_path):
        """直接从物理数据目录提供文档图片"""
        # 构建完整的图片物理路径
        full_path = os.path.join(DOCUMENT_IMAGES_DIR, image_path)
        
        # 检查文件是否存在
        if not os.path.isfile(full_path):
            logging.warning(f"请求的图片不存在: {full_path}")
            # 返回404或占位符图片
            return app.send_static_file('images/image_placeholder.png')
            
        # 获取图片目录
        image_dir = os.path.dirname(full_path)
        if not os.path.exists(image_dir):
            logging.warning(f"图片目录不存在: {image_dir}")
            return app.send_static_file('images/image_placeholder.png')
        
        # 获取图片文件名
        filename = os.path.basename(full_path)
        
        # 从数据目录发送文件
        return send_from_directory(image_dir, filename)
    
    return app

def _create_file_handler(log_date):
    """创建基于日期的文件处理器
    
    Args:
        log_date: 日期字符串，格式为YYYY-MM-DD
        
    Returns:
        RotatingFileHandler: 配置好的日志处理器
    """
    # 确保日志目录存在
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # 使用日期作为日志文件名的一部分
    log_file = os.path.join(LOG_DIR, f"{log_date}_{LOG_FILE}")
    
    # 创建日志格式化器
    log_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] - %(name)s - %(message)s")
    
    # 创建文件处理器（使用循环日志文件）并指定UTF-8编码
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    
    return file_handler

def _update_log_file_handler(log_date):
    """更新根日志记录器的文件处理器
    
    Args:
        log_date: 日期字符串，格式为YYYY-MM-DD
    """
    # 获取根记录器
    root_logger = logging.getLogger()
    
    # 移除现有的文件处理器
    for handler in root_logger.handlers[:]:
        if isinstance(handler, RotatingFileHandler):
            root_logger.removeHandler(handler)
    
    # 添加新的文件处理器
    file_handler = _create_file_handler(log_date)
    root_logger.addHandler(file_handler)
    
    # 记录一次日志更新信息
    logging.info(f"已更新日志文件为: {log_date}_{LOG_FILE}")

def _setup_logging():
    """设置日志系统"""
    global _last_log_date, _log_updated_today
    
    # 获取当前日期
    today = datetime.now().strftime('%Y-%m-%d')
    _last_log_date = today
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # 移除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加文件处理器
    file_handler = _create_file_handler(today)
    root_logger.addHandler(file_handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] - %(name)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 记录一次日志更新信息
    logging.info(f"日志系统初始化完成，使用日志文件: {today}_{LOG_FILE}")
    _log_updated_today = True
    
    # 清理旧日志文件（超过7天的日志）
    try:
        # 计算7天前的日期
        days_to_keep = 7
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_timestamp = cutoff_date.timestamp()
        
        # 查找所有日志文件
        log_pattern = os.path.join(LOG_DIR, "*.log*")
        for log_file in glob.glob(log_pattern):
            # 获取文件修改时间
            file_mtime = os.path.getmtime(log_file)
            # 如果文件早于截止日期，则删除
            if file_mtime < cutoff_timestamp:
                try:
                    os.remove(log_file)
                    print(f"已删除旧日志文件: {log_file}")
                except Exception as e:
                    print(f"无法删除日志文件 {log_file}: {e}")
    except Exception as e:
        print(f"日志清理过程中出错: {e}")

# 导入应用实例，方便import
app = create_app()
