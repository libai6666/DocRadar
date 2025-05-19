import os
import secrets
import json

# 应用根目录
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 数据库配置
DATABASE = os.path.join(BASE_DIR, 'docradar.db')

# SQLite优化配置
SQLITE_CONFIG = {
    'timeout': 30,           # 等待锁定的超时时间（秒）
    'isolation_level': None, # 自动提交模式
    'check_same_thread': False, # 允许多线程访问
    'uri': True              # 使用URI连接方式，支持更多配置
}

# 修改DATABASE为URI格式，启用WAL模式提高并发性能
DATABASE_URI = f"file:{DATABASE}?mode=rwc&journal_mode=WAL&cache=shared"

# 最大数据库连接池数
DB_POOL_SIZE = 10

# 开发模式
DEBUG = False  # 生产环境设为False

# 文件上传配置
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
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
SECRET_KEY = secrets.token_hex(32)  # 使用随机生成的密钥
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

# 管理功能配置
def get_admin_key():
    """
    获取管理员密钥，优先级：配置文件 > 环境变量 > 随机生成
    注意：如果配置文件中ADMIN_KEY存在（即使是空字符串），也会使用配置文件的值
    """
    admin_config_path = os.path.join(BASE_DIR, 'admin_config.json')
    
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
    
    # 尝试从环境变量读取
    env_key = os.environ.get('DOCRADAR_ADMIN_KEY')
    if env_key is not None:  # 修改：检查是否为None而不是隐式转换为布尔值
        return env_key
        
    # 随机生成
    return secrets.token_hex(8)
    
ADMIN_KEY = get_admin_key() 