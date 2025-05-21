# DocRadar 日志管理

## 日志系统概述

DocRadar 使用分层的日志管理策略:

1. **环境分离** - 测试和生产环境的日志分别存储在不同目录
2. **日期标识** - 日志文件名包含日期信息
3. **自动清理** - 超过7天的日志会被自动删除
4. **UTF-8编码** - 支持中文和其他特殊字符正确显示

## 日志文件位置

- 测试环境: `logs/test/YYYY-MM-DD_docradar.log`
- 生产环境: `logs/production/YYYY-MM-DD_docradar.log`

## 日志清理

系统提供两种方式清理过期日志:

1. **启动时清理** - 应用启动时会自动清理超过7天的日志
2. **定时任务清理** - 通过计划任务每日执行清理脚本

## 设置定时清理任务

### Windows (使用任务计划程序)

1. 打开任务计划程序
2. 创建基本任务
3. 设置名称为"DocRadar日志清理"
4. 设置每天执行一次
5. 设置开始时间（如凌晨2:00）
6. 设置操作为"启动程序"
7. 程序/脚本设置为 `python` 或 Python 完整路径
8. 添加参数 `scripts/cleanup_logs.py`
9. 起始位置设置为DocRadar项目根目录

例如:
```
程序/脚本: C:\Python39\python.exe
添加参数: scripts/cleanup_logs.py
起始位置: D:\tools\Pycharm\PycharmWork\DocRadar
```

### Linux/Mac (使用crontab)

编辑crontab:
```bash
crontab -e
```

添加以下内容，在每天凌晨2:00执行清理:
```
0 2 * * * cd /path/to/DocRadar && python scripts/cleanup_logs.py
```

## 手动执行清理

可以随时手动执行清理脚本:

```bash
python scripts/cleanup_logs.py
```

## 日志格式

DocRadar使用以下日志格式:
```
%(asctime)s [%(levelname)s] - %(name)s - %(message)s
```

例如:
```
2025-05-20 19:44:39,429 [INFO] - root - 搜索 'adjustments' 找到 1 个结果
``` 