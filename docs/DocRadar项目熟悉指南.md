# DocRadar项目熟悉指南

本指南将帮助你系统性地熟悉DocRadar本地文档搜索系统，从整体架构到具体实现细节，确保你能够全面掌握这个系统的各个方面。

## 1. 系统概览

DocRadar是一个基于Flask的本地文档管理和搜索系统，专为解决在大量产品文档中查找特定内容的问题而设计。系统支持多种文档格式，提供高效的搜索功能，并支持多环境部署。

### 1.1 核心功能

- **文档上传与管理**：支持PDF、Word、TXT文档的上传、存储和管理
- **文档内容解析**：自动提取文本内容、图片和格式化信息
- **全文检索**：基于SQLite FTS5的高效搜索功能
- **搜索结果导航**：在文档中高亮显示匹配内容并支持导航
- **多环境支持**：测试/生产环境数据隔离

### 1.2 项目目录结构

```
DocRadar/
├── app/                    # 主应用目录
│   ├── __init__.py         # 应用初始化
│   ├── core/               # 核心功能模块
│   │   ├── config.py       # 配置管理
│   │   ├── routes.py       # 主路由
│   │   ├── document_routes.py  # 文档相关路由
│   │   ├── search_routes.py    # 搜索相关路由
│   │   └── admin_routes.py     # 管理功能路由
│   ├── models/             # 数据模型
│   ├── static/             # 静态资源
│   │   ├── css/            # 样式文件
│   │   ├── js/             # JavaScript文件
│   │   └── images/         # 图片资源
│   ├── templates/          # HTML模板
│   └── utils/              # 工具类
│       ├── document_parser.py  # 文档解析器
│       ├── search_engine.py    # 搜索引擎
│       └── storage.py          # 存储管理
├── config/                 # 配置文件目录
├── data/                   # 数据存储目录
│   ├── test/               # 测试环境数据
│   └── production/         # 生产环境数据
├── logs/                   # 日志目录
├── app.py                  # 应用入口点
├── requirements.txt        # 依赖列表
├── Dockerfile              # Docker配置
└── docker-compose.yml      # Docker Compose配置
```

## 2. 技术栈详解

### 2.1 后端技术栈

- **Web框架**：Flask - 轻量级Python Web框架
- **数据存储**：
  - SQLite数据库 - 支持FTS5全文检索
  - 文件系统 - 分层目录结构存储文档和图片
- **文档处理**：
  - PyPDF2/pdfplumber - PDF文件解析
  - python-docx - Word文档解析
  - mammoth - DOCX到HTML的转换
- **会话管理**：Flask-Session - 服务器端会话存储
- **安全组件**：Flask-WTF - CSRF保护
- **部署工具**：Gunicorn, Docker - 生产环境部署

### 2.2 前端技术栈

- **基础框架**：HTML5, CSS3, JavaScript (ES6+)
- **UI框架**：Bootstrap 5 - 响应式设计
- **图标库**：Bootstrap Icons
- **AJAX处理**：原生Fetch API
- **自定义组件**：
  - SearchNavigator - 文档内搜索导航
  - 文件上传管理器 - 处理拖放和批量上传
  - 搜索标签系统 - 管理搜索历史

## 3. 核心模块详解

### 3.1 应用初始化与配置 (app.py, app/__init__.py, app/core/config.py)

#### 应用入口 (app.py)
```python
def main():
    # 默认参数
    env = 'test'
    
    # 解析命令行参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ('--env', '-e') and i + 1 < len(args):
            env = args[i + 1]
            i += 2
        else:
            i += 1
    
    # 设置环境变量
    os.environ['DOCRADAR_ENV'] = env
    
    # 导入并运行应用
    from app import app
    from app.core.config import HOST, PORT, DEBUG
    
    # 运行应用
    app.run(host=HOST, port=PORT, debug=DEBUG)
```

这个文件是系统的入口点，负责解析命令行参数，设置环境变量，并启动Flask应用。

#### 应用初始化 (app/__init__.py)
```python
def create_app(test_config=None):
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
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(compat_bp)
    
    # 其他初始化...
    
    return app

# 创建应用实例
app = create_app()
```

这个文件负责创建和配置Flask应用实例，注册蓝图，设置模板过滤器和错误处理器。

#### 配置管理 (app/core/config.py)
```python
# 环境设置
ENV = os.environ.get('DOCRADAR_ENV', 'test')

# 根据环境设置不同的主机地址
if ENV == 'test':
    HOST = '127.0.0.1'
    PORT = 5000
else:  # production
    HOST = '192.168.0.110'
    PORT = 5000

# 数据目录 - 根据环境设置不同的数据目录
if ENV == 'test':
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(ROOT_DIR, 'data', 'test'))
else:  # production
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(ROOT_DIR, 'data', 'production'))
```

这个文件管理系统的所有配置参数，包括环境设置、路径配置、数据库设置等，实现了测试和生产环境的隔离。

### 3.2 文档处理模块 (app/utils/document_parser.py)

这个模块负责解析不同类型的文档并提取内容：

```python
class DocumentParser(ABC):
    """文档解析器抽象基类"""

    @abstractmethod
    def parse(self, file_path):
        """解析文档内容"""
        pass

    @staticmethod
    def get_parser(file_path):
        """根据文件类型获取合适的解析器"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return PdfParser()
        elif ext in ('.docx', '.doc'):
            return DocxParser()
        elif ext == '.txt':
            return TxtParser()
        else:
            raise ValueError(f"不支持的文件类型: {ext}")
```

系统实现了三种解析器：
- **PdfParser**：使用PyPDF2和pdfplumber解析PDF文件
- **DocxParser**：使用python-docx解析Word文档，mammoth转换为HTML
- **TxtParser**：处理纯文本文件，支持多种编码

特别注意DocxParser的实现，它不仅提取文本，还能处理文档中的图片：

```python
def _extract_images(self, file_path, doc_id=None):
    """提取DOCX文档中的图片，包括尺寸信息"""
    # 创建图片存储目录
    image_dir, rel_path = self._get_image_directory(file_path, doc_id)
    
    # 打开docx文件
    from zipfile import ZipFile
    z = ZipFile(file_path)
    
    # 提取所有图片文件
    image_mappings = {}
    
    for zinfo in z.filelist:
        if zinfo.filename.startswith('word/media/'):
            # 处理图片...
```

### 3.3 存储管理模块 (app/utils/storage.py)

这个模块负责文件存储和元数据管理：

```python
class Storage:
    """存储管理类，负责文件存储和元数据管理"""
    
    def __init__(self, uploads_dir=UPLOADS_DIR, db_path=DATABASE_URI):
        self.uploads_dir = uploads_dir
        self.db_path = db_path
        self._ensure_dirs()
        self.init_db()
```

主要功能包括：
- 文件保存和命名
- 数据库初始化和管理
- 文档元数据和内容存储
- 文件存在性检查和覆盖处理

关键方法：
```python
def save_file(self, file, filename, is_overwrite=False):
    """保存上传的文件"""
    # 生成安全的文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    safe_filename = f"{timestamp}_{random_str}_{secure_filename(filename)}"
    
    # 创建年月子目录
    year_month = datetime.now().strftime('%Y%m')
    year_month_dir = os.path.join(self.uploads_dir, year_month)
    
    # 确保目录存在
    if not os.path.exists(year_month_dir):
        os.makedirs(year_month_dir, exist_ok=True)
    
    # 构建文件路径
    file_path = os.path.join(year_month_dir, safe_filename)
    
    # 保存文件
    file.save(file_path)
    
    return file_path
```

### 3.4 搜索引擎模块 (app/utils/search_engine.py)

这个模块实现了基于SQLite的搜索功能：

```python
class SearchEngine:
    """基于SQL LIKE的搜索引擎"""
    
    def search(self, query, limit=SEARCH_RESULT_LIMIT):
        """搜索文档"""
        if not query:
            return []
            
        results = []
        
        try:
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 使用LIKE搜索
            sql = '''
            SELECT 
                d.id, d.title, d.file_type, d.file_size, d.created_at, d.original_filename,
                dc.content
            FROM 
                documents d
            JOIN 
                document_content dc ON d.id = dc.doc_id
            WHERE 
                d.title LIKE ? OR
                dc.content LIKE ?
            ORDER BY 
                d.created_at DESC
            LIMIT ?
            '''
            
            search_pattern = f"%{query}%"
            cursor.execute(sql, (search_pattern, search_pattern, limit))
            # 处理结果...
```

特别注意预览生成和高亮处理的实现：

```python
def _generate_preview(self, content, query):
    """根据搜索词生成内容预览"""
    # 查找搜索词的位置
    lower_content = content.lower()
    lower_query = query.lower()
    
    positions = []
    start_pos = 0
    while True:
        pos = lower_content.find(lower_query, start_pos)
        if pos == -1:
            break
        positions.append(pos)
        start_pos = pos + len(query)
    
    # 如果找不到精确匹配，使用模糊匹配
    if not positions:
        words = query.lower().split()
        for word in words:
            if len(word) > 2:  # 忽略太短的词
                # 模糊匹配处理...
```

### 3.5 路由与视图模块

#### 主路由 (app/core/routes.py)
```python
@main_bp.route('/')
@login_required
def index():
    """首页路由"""
    # 获取分页和搜索参数
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('search', '')
    
    # 获取文档（带分页）
    documents_data = storage.get_all_documents(page=page, limit=limit, search_query=search)
    
    # 获取搜索历史
    search_history = get_search_history()
    
    return render_template(
        'index.html', 
        documents=documents_data['documents'], 
        pagination=documents_data['pagination'],
        search_query=search,
        search_history=search_history
    )
```

#### 文档路由 (app/core/document_routes.py)
```python
@document_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """单个文档上传处理"""
    # 检查请求中是否有文件
    if 'file' not in request.files:
        flash('没有提供文件')
        return redirect(request.referrer or url_for('main.index'))
    
    file = request.files['file']
    
    # 检查文件名是否为空
    if file.filename == '':
        flash('未选择文件')
        return redirect(request.referrer or url_for('main.index'))
    
    # 检查覆盖选项
    overwrite = request.form.get('overwrite', 'false') == 'true'
    
    # 处理文件上传
    result = process_upload(file, overwrite)
    
    # 处理结果...
```

#### 搜索路由 (app/core/search_routes.py)
```python
@search_bp.route('', methods=['GET'])
@login_required
def search():
    """搜索页面"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    # 如果没有查询参数，显示基本搜索页面
    if not query:
        search_history = get_search_history()
        return render_template('results.html', 
                              query='',
                              results=[],
                              search_history=search_history,
                              history_id=None,
                              has_results=False)
    
    # 执行搜索
    results = search_engine.search(query, limit=SEARCH_RESULT_LIMIT)
    
    # 记录搜索历史
    history_id = add_search_history(query, results)
    search_history = get_search_history()
    
    # 返回结果...
```

## 4. 前端实现

### 4.1 模板系统

系统使用Flask的Jinja2模板引擎，主要模板包括：
- `index.html` - 首页，显示文档列表
- `results.html` - 搜索结果页面
- `view.html` - 文档查看页面
- `login.html` - 登录页面

模板使用Bootstrap 5进行响应式布局，确保在不同设备上都有良好的显示效果。

### 4.2 JavaScript组件

#### 搜索导航器 (search-navigator.js)
```javascript
class SearchNavigator {
    constructor() {
        this.currentIndex = 0;
        this.totalMatches = 0;
        this.matches = [];
        this.query = '';
        this.isActive = false;
        
        // 导航控件
        this.container = null;
        this.counter = null;
        this.prevButton = null;
        this.nextButton = null;
        this.closeButton = null;
    }
    
    init(query) {
        if (!query) return;
        
        this.query = query;
        
        // 查找匹配项
        this.findMatches();
        
        if (this.totalMatches > 0) {
            this.createNavigation();
            this.navigateToMatch(0);
            this.isActive = true;
        }
    }
    
    // 其他方法...
}
```

这个组件负责在文档查看页面中实现搜索导航功能，包括高亮显示匹配项、在匹配项之间导航等。

#### 文件上传管理器 (main.js)
```javascript
// 文件拖放处理
function setupFileDrop() {
    const dropArea = document.getElementById('drop-area');
    if (!dropArea) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    dropArea.addEventListener('drop', handleDrop, false);
}

// 处理文件拖放
function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    handleFiles(files);
}

// 处理文件上传
function handleFiles(files) {
    // 处理文件上传...
}
```

这个组件处理文件上传相关的交互，包括拖放上传、批量上传、上传进度显示等。

### 4.3 CSS样式

系统使用自定义的CSS样式（style.css）和Bootstrap 5，主要样式包括：

```css
/* 搜索结果样式 */
.search-result-item {
    transition: all 0.3s ease;
    position: relative;
    border-left: 4px solid transparent;
}

.search-result-item:hover {
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

/* 高亮样式 */
mark {
    background-color: #fff5b1;
    padding: 0.1em 0.2em;
    border-radius: 2px;
    font-weight: bold;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,0.1);
}

/* 当前匹配项高亮 */
mark.current-match {
    background-color: #ffcc00;
    box-shadow: 0 0 0 2px rgba(255, 204, 0, 0.5);
    animation: pulse 1s infinite;
}
```

## 5. 数据流程

### 5.1 文档上传流程

1. 用户选择文件或拖放文件到上传区域
2. 前端验证文件类型和大小
3. 发送文件到后端（`/document/upload`或`/document/upload/batch`）
4. 后端处理：
   - 文件存储到文件系统（`storage.save_file`）
   - 解析文档内容（`DocumentParser.parse`）
   - 提取元数据和文本内容
   - 存储到数据库（`storage.add_document_metadata`和`storage.add_document_content`）
5. 返回上传结果给前端

### 5.2 搜索流程

1. 用户输入搜索词并提交
2. 后端处理：
   - 执行搜索查询（`search_engine.search`）
   - 生成结果预览和高亮
   - 记录搜索历史
3. 返回结果页面给用户
4. 用户点击结果查看文档
5. 前端搜索导航器（`SearchNavigator`）处理文档内导航

## 6. 如何运行系统

### 6.1 本地运行

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行测试环境
python app.py -e test

# 运行生产环境
python app.py -e production
```

### 6.2 Docker运行

```bash
# 构建Docker镜像
docker-compose build

# 启动服务
docker-compose up -d
```

## 7. 如何修改或扩展功能

### 7.1 添加新的文档类型支持

1. 在`app/core/config.py`中的`ALLOWED_EXTENSIONS`添加新的文件类型
2. 在`app/utils/document_parser.py`中创建新的解析器类
3. 更新`DocumentParser.get_parser`方法以支持新的文件类型

### 7.2 改进搜索功能

1. 修改`app/utils/search_engine.py`中的`search`方法
2. 可以考虑实现更高级的排序算法或过滤功能

### 7.3 添加用户管理功能

1. 扩展`app/core/auth.py`中的认证系统
2. 添加用户管理相关的路由和视图
3. 创建用户管理界面模板

## 8. 调试与日志

系统使用Python的标准日志模块，日志文件存储在：
- 测试环境：`logs/test/YYYY-MM-DD_docradar_test.log`
- 生产环境：`logs/production/YYYY-MM-DD_docradar_prod.log`

可以通过查看日志文件来诊断问题。

## 9. 总结

DocRadar是一个功能完整的文档管理和搜索系统，采用Flask框架构建，具有良好的模块化设计。通过本指南，你应该能够理解系统的整体架构、核心模块和数据流程，为进一步开发和定制系统打下基础。

要深入理解某个特定功能，建议从相应的路由入手，追踪代码流程，了解前后端的交互方式和数据处理逻辑。 