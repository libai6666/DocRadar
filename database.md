# DocRadar数据库表结构说明

DocRadar使用SQLite数据库来存储文档信息和全文搜索索引。以下是各个表的详细说明：

## 1. documents表

存储上传文档的元数据信息。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| id | INTEGER | 主键，自动递增 |
| filename | TEXT | 原始文件名 |
| filepath | TEXT | 文件在服务器上的存储路径 |
| title | TEXT | 文档标题，通常从文档内容中提取 |
| file_type | TEXT | 文件MIME类型 |
| file_size | INTEGER | 文件大小(字节) |
| metadata | TEXT | 文档元数据(JSON格式) |
| created_at | TIMESTAMP | 上传时间，默认为当前时间 |
| original_filename | TEXT | 上传时的原始文件名，保留用户的完整文件名 |

## 2. document_content表

使用FTS5(全文搜索)扩展创建的虚拟表，用于存储文档内容并支持全文搜索。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| doc_id | INTEGER | 文档ID，关联documents表的id字段(未索引) |
| content | TEXT | 文档内容，用于全文搜索 |

## 3. document_html_content表

存储文档的HTML格式内容，用于更好地保留文档原始格式（尤其是DOCX文档）。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| doc_id | INTEGER | 主键，文档ID，关联documents表的id字段 |
| html_content | TEXT | 文档的HTML格式内容，包含格式和图片链接 |

## 4. document_content_xxx表

这些是document_content表的辅助表，由FTS5自动创建：

- **document_content_data**: 存储文档内容的原始数据
  | 字段名 | 类型 | 说明 |
  |-------|------|------|
  | id | INTEGER | 记录ID |
  | block | BLOB | 分块存储的内容数据 |

- **document_content_idx**: 存储全文搜索索引
  | 字段名 | 类型 | 说明 |
  |-------|------|------|
  | segid | INTEGER | 索引段ID |
  | term | TEXT | 索引词 |
  | pgno | INTEGER | 页码 |

- **document_content_content**: 存储分词后的内容
- **document_content_docsize**: 存储每个文档的大小统计信息
  | 字段名 | 类型 | 说明 |
  |-------|------|------|
  | id | INTEGER | 文档ID |
  | sz | INTEGER | 文档大小 |

- **document_content_config**: 存储FTS5配置信息
  | 字段名 | 类型 | 说明 |
  |-------|------|------|
  | k | TEXT | 配置项名称 |
  | v | TEXT | 配置项值 |

## 5. sqlite_sequence表

SQLite自动创建的表，用于跟踪自增主键的当前值。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| name | TEXT | 表名 |
| seq | INTEGER | 当前序列值 |

## 数据库表关系

```
documents
   ↑
   |------ document_content (FTS5虚拟表，通过doc_id关联)
   |
   |------ document_html_content (通过doc_id关联)
```

- **documents表**是核心表，存储所有文档的基本信息和元数据
- **document_content表**通过doc_id字段与documents表关联，存储用于全文搜索的文本内容
- **document_html_content表**通过doc_id字段与documents表关联，存储格式化的HTML内容
- 当删除documents表中的记录时，相关的document_content和document_html_content记录也会通过外键约束被删除

## 全文搜索实现

DocRadar使用SQLite的FTS5扩展实现全文搜索功能。搜索流程如下：

1. 当用户上传文档时，系统将文档内容提取并存储到document_content表
2. 对于DOCX等富文本文档，系统还会生成HTML版本并存储到document_html_content表
3. 用户搜索时，系统首先在document_content表中执行FTS5全文搜索
4. 如果FTS5搜索失败或无结果，系统会回退到基于LIKE的模糊匹配搜索
5. 搜索结果会显示匹配内容的上下文，并在查看文档时高亮显示匹配词

## 批量上传文件功能说明

DocRadar支持批量上传文件功能，使用方法如下：

1. 在首页点击"选择文件"按钮，可以选择多个文件(按住Ctrl键选择多个文件)
2. 或直接将多个文件拖放到虚线框内
3. 选择文件后，界面会显示所选文件列表和"开始上传"按钮
4. 点击"开始上传"按钮，系统会逐个上传文件并显示进度
5. 上传完成后会自动刷新页面，显示所有上传的文档

支持的文件格式：PDF、DOCX/DOC、TXT

## 数据库管理功能说明

DocRadar提供了数据库管理功能，可以查看和编辑数据库内容：

1. 访问地址：http://localhost:5000/admin/db?key=YOUR_ADMIN_KEY
2. ADMIN_KEY在admin_config.json文件中配置
3. 支持查看表结构、表数据、执行SQL查询、导出CSV等功能
4. 可以添加、编辑、删除记录

## 搜索历史和缓存

搜索历史记录存储在用户会话(session)中，而不是数据库中，结构如下：

```
session['search_history'] = [
    {
        'id': 1,
        'query': '搜索关键词',
        'timestamp': '2023-01-01 12:00:00',
        'results': [搜索结果列表]
    },
    ...
]
```

用户可以删除单个搜索记录或清空所有搜索历史。搜索历史仅在用户会话有效期内保留。 