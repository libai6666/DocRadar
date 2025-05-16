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

## 2. document_content表

使用FTS5(全文搜索)扩展创建的虚拟表，用于存储文档内容并支持全文搜索。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| doc_id | INTEGER | 文档ID，关联documents表的id字段(未索引) |
| content | TEXT | 文档内容，用于全文搜索 |
| title | TEXT | 文档标题，用于全文搜索 |

## 3. document_content_xxx表

这些是document_content表的辅助表，由FTS5自动创建：

- document_content_data: 存储文档内容的原始数据
- document_content_idx: 存储全文搜索索引
- document_content_content: 存储分词后的内容
- document_content_docsize: 存储每个文档的大小统计信息
- document_content_config: 存储FTS5配置信息

## 4. sqlite_sequence表

SQLite自动创建的表，用于跟踪自增主键的当前值。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| name | TEXT | 表名 |
| seq | INTEGER | 当前序列值 |

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