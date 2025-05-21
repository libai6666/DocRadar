import os
import secrets
import json
import logging
import platform

# 环境设置 - 检测当前环境
# 可以是 'test' 或 'production'
ENV = os.environ.get('DOCRADAR_ENV', 'test')

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# 根据环境设置不同的主机地址
if ENV == 'test':
    HOST = '127.0.0.1'
    PORT = 5000
else:  # production
    HOST = '192.168.0.110'
    PORT = 5000

# 记录当前环境
logging.info(f"当前环境: {ENV}, 主机: {HOST}")

# 应用目录
APP_DIR = os.path.join(ROOT_DIR, 'app')

# 数据目录 - 根据环境设置不同的数据目录
if ENV == 'test':
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(ROOT_DIR, 'data', 'test'))
else:  # production
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(ROOT_DIR, 'data', 'production'))

UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')
DB_DIR = os.path.join(DATA_DIR, 'db')

# 日志目录
if ENV == 'test':
    LOG_DIR = os.path.join(ROOT_DIR, 'logs', 'test')
else:  # production
    LOG_DIR = os.path.join(ROOT_DIR, 'logs', 'production')

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FILE = 'docradar.log'

# 确保目录存在
for directory in [DATA_DIR, UPLOADS_DIR, DB_DIR, LOG_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# 数据库配置 - 根据环境设置不同的数据库文件
if ENV == 'test':
    DB_NAME = 'docradar_test.db'
else:  # production
    DB_NAME = 'docradar_prod.db'

DATABASE = os.path.join(DB_DIR, DB_NAME)

# SQLite优化配置
SQLITE_CONFIG = {
    'timeout': 30,           # 等待锁定的超时时间（秒）
    'isolation_level': None, # 自动提交模式
    'check_same_thread': False, # 允许多线程访问
    'uri': True              # 使用URI连接方式，支持更多配置
}

# 修改DATABASE为URI格式，启用WAL模式提高并发性能
# 特殊处理Windows平台的路径格式
if platform.system() == 'Windows':
    # Windows路径格式
    DATABASE_NORMALIZED = DATABASE.replace('\\', '/')
    DATABASE_URI = DATABASE_NORMALIZED
else:
    # 非Windows平台使用URI格式
    DATABASE_URI = f"file:{DATABASE}?mode=rwc&journal_mode=WAL&cache=shared"

# 最大数据库连接池数
DB_POOL_SIZE = 10

# 开发模式 - 测试环境下默认启用调试模式
DEBUG = os.environ.get('FLASK_DEBUG', ENV == 'test')

# 文件上传配置
UPLOAD_FOLDER = UPLOADS_DIR
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB 最大上传文件大小

# 支持的文档类型
ALLOWED_EXTENSIONS = {
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'doc': 'application/msword',
    'txt': 'text/plain',
}

# 搜索引擎配置
SEARCH_RESULT_LIMIT = 20  # 搜索结果限制数量
PREVIEW_LENGTH = 200  # 预览内容长度（字符数）

# 安全配置
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))  # 使用环境变量或随机生成的密钥
SESSION_COOKIE_SECURE = False  # 本地开发环境使用 HTTP
SESSION_COOKIE_HTTPONLY = True  # 防止JavaScript访问cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # 防止CSRF攻击

# CSP配置
CSP = {
    'default-src': ["'self'", "https:", "http:"],
    'script-src': [
        "'self'",
        "'unsafe-inline'",
        "'unsafe-eval'",
        "https://cdn.jsdelivr.net",
        "https://code.jquery.com"
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",
        "https://cdn.jsdelivr.net"
    ],
    'img-src': ["'self'", "data:", "https:", "http:"],
    'font-src': ["'self'", "https://cdn.jsdelivr.net", "http:"],
    'connect-src': ["'self'", "http:", "https:"]
}

# 定义配置文件路径
def get_config_path(filename):
    """获取配置文件路径"""
    return os.path.join(ROOT_DIR, 'config', filename)

# 管理功能配置
def get_admin_key():
    """
    获取管理员密钥，优先级：环境变量 > 配置文件 > 随机生成
    """
    # 尝试从环境变量读取
    env_key = os.environ.get('ADMIN_KEY')
    if env_key:
        return env_key
    
    # 根据环境确定配置文件路径
    if ENV == 'production':
        admin_config_path = get_config_path('admin_config_production.json')
    else:  # test
        admin_config_path = get_config_path('admin_config_test.json')
    
    # 尝试从配置文件读取
    if os.path.exists(admin_config_path):
        try:
            with open(admin_config_path, 'r') as f:
                config_data = json.load(f)
                # 检查ADMIN_KEY是否存在，空字符串就不接受
                if 'ADMIN_KEY' in config_data and config_data['ADMIN_KEY']:
                    return config_data['ADMIN_KEY']
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    # 如果配置文件不存在或读取失败，创建一个新的配置文件
    try:
        # 随机生成密钥
        new_key = secrets.token_hex(8)
        config_data = {"ADMIN_KEY": new_key}
        
        # 确保目录存在
        os.makedirs(os.path.dirname(admin_config_path), exist_ok=True)
        
        # 写入配置文件
        with open(admin_config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"已创建新的管理员配置文件: {admin_config_path}")
        print(f"ADMIN_KEY: {new_key}")
        
        return new_key
    except Exception as e:
        print(f"创建配置文件失败: {e}")
        # 如果还是失败，返回随机生成的密钥
        return secrets.token_hex(8)
    
ADMIN_KEY = get_admin_key() 