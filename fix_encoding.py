#!/usr/bin/env python
"""
修复Python文件的编码问题
"""

import os

def fix_file_encoding(file_path):
    """修复文件编码问题"""
    try:
        # 读取文件内容（二进制模式）
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 尝试删除BOM标记
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]  # 跳过BOM
        
        # 处理可能的其他非法字符
        try:
            # 尝试解码并重新编码为utf-8
            decoded = content.decode('utf-8', errors='ignore')
            content = decoded.encode('utf-8')
        except UnicodeDecodeError:
            # 如果utf-8解码失败，尝试用其他编码
            try:
                decoded = content.decode('cp1252', errors='ignore')
                content = decoded.encode('utf-8')
            except UnicodeDecodeError:
                # 若还是失败，直接替换所有不可见字符
                import re
                content = re.sub(br'[\x00-\x1f\x7f-\xff]', b'', content)
        
        # 写回文件
        with open(file_path, 'wb') as f:
            f.write(content)
        
        print(f"修复了文件编码: {file_path}")
        return True
    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def recreate_init_file(file_path):
    """重新创建__init__.py文件"""
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    
    # 根据目录确定文件内容
    if 'app' == directory:
        content = '''"""
DocRadar应用初始化模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template

# 尝试导入CSRF保护
try:
    from flask_wtf.csrf import CSRFProtect
    has_csrf = True
except ImportError:
    has_csrf = False
    print("警告: flask-wtf模块未安装，CSRF保护将不可用")

from app.core.config import SECRET_KEY, LOG_DIR, LOG_LEVEL, LOG_FILE
from app.core.routes import main_bp
from app.core.document_routes import document_bp
from app.core.search_routes import search_bp
from app.core.admin_routes import admin_bp

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
    )
    
    # 初始化CSRF保护
    if has_csrf:
        csrf = CSRFProtect(app)
    
    # 配置日志
    _setup_logging()
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(admin_bp)
    
    # 错误处理
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404
    
    @app.errorhandler(500)
    def server_error(e):
        logging.error(f"服务器错误: {e}")
        return render_template("500.html"), 500
    
    return app

def _setup_logging():
    """设置日志系统"""
    # 确保日志目录存在
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # 配置根日志记录器
    log_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] - %(name)s - %(message)s")
    
    # 获取根记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # 移除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加文件处理器（使用循环日志文件）
    log_file = os.path.join(LOG_DIR, LOG_FILE)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

# 导入应用实例，方便import
app = create_app()
'''
    elif 'app/core' in directory:
        content = '''"""
DocRadar - 核心模块包
包含系统的核心功能模块
"""
'''
    elif 'app/utils' in directory:
        content = '''"""
DocRadar - 工具模块包
包含系统使用的各种工具类
"""
'''
    elif 'app/models' in directory:
        content = '''"""
DocRadar - 数据模型包
包含系统中使用的数据模型类
"""

# 未来可以导入模型类，例如：
# from .document_model import Document
# from .user_model import User
'''
    elif 'tests' in directory:
        content = '''"""
DocRadar - 测试模块包
包含系统的单元测试和集成测试
"""
'''
    else:
        content = '''"""
DocRadar - 模块初始化文件
"""
'''
    
    try:
        # 删除旧文件
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 创建新文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"重新创建了文件: {file_path}")
        return True
    except Exception as e:
        print(f"重新创建文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    problematic_files = [
        'app/__init__.py',
        'app/core/__init__.py',
        'app/utils/__init__.py',
        'app/models/__init__.py',
        'tests/__init__.py'
    ]
    
    print("开始修复问题文件...")
    for file_path in problematic_files:
        # 先尝试修复编码
        if os.path.exists(file_path):
            fix_file_encoding(file_path)
        
        # 如果修复不成功或文件不存在，直接重新创建
        recreate_init_file(file_path)
    
    print("文件修复完成。")

if __name__ == '__main__':
    main() 