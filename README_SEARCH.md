# DocRadar 搜索实现说明

## 搜索机制

DocRadar系统使用**标准SQL LIKE查询**来实现文档搜索功能，而非SQLite的FTS5全文索引。

### 主要优势

1. **简单可靠** - 使用标准SQL LIKE查询，不依赖于特定的SQLite扩展，确保在各种环境下可靠运行
2. **易于维护** - 代码结构清晰，实现简单，容易理解和维护
3. **兼容性好** - 在各种SQLite版本下均可正常工作，没有额外依赖

### 搜索实现逻辑

1. 用户输入搜索关键词
2. 系统使用SQL LIKE查询，在文档标题和内容中搜索匹配项
3. 为每个结果生成带有高亮的内容预览
4. 搜索结果按文档创建时间倒序排列
5. 搜索历史保存在用户会话中，方便快速访问历史搜索

### 代码结构

- `app/utils/search_engine.py` - 搜索引擎实现，使用SQL LIKE进行查询
- `app/utils/storage.py` - 文档存储管理，包含标准SQL表结构定义
- `app/core/search_routes.py` - 搜索相关的路由和历史记录管理

### 数据库表结构

搜索功能主要依赖以下标准SQL表：

```sql
-- 文档元数据表
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    title TEXT,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    original_filename TEXT
);

-- 文档内容表
CREATE TABLE document_content (
    doc_id INTEGER PRIMARY KEY,
    content TEXT,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- HTML内容表
CREATE TABLE document_html_content (
    doc_id INTEGER PRIMARY KEY,
    html_content TEXT,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

## 注意事项

1. 对于大型文档库，SQL LIKE查询性能可能较低，未来可考虑实现缓存或优化查询策略
2. 搜索目前不支持高级操作符（AND, OR等），仅支持简单关键词匹配
3. 目前不支持中文分词，对中文文档的搜索精度可能较低

## 未来优化方向

1. 实现简单的中文分词
2. 添加更多搜索过滤条件（按文件类型、日期等）
3. 提高大型文档库的搜索性能 