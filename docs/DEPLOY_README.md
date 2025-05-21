# DocRadar 部署说明

## 部署选项概述

DocRadar提供三种主要部署方式，您可以根据自己的需求选择最合适的方式：

1. **局域网部署**（基础选项）：适合小型团队在局域网内共享使用
2. **Docker容器化部署**（推荐选项）：提供更好的隔离性和可移植性
3. **云服务器部署**（高级选项）：支持互联网访问，需要额外配置安全措施

## 环境配置

DocRadar支持测试环境和生产环境的区分，两种环境使用完全不同的数据存储路径，相互隔离：

- **测试环境**：数据存储在 `./data/test/` 目录，IP地址为 `127.0.0.1`
- **生产环境**：数据存储在 `./data/production/` 目录，IP地址为 `192.168.0.110`

### 环境变量设置

通过设置环境变量 `DOCRADAR_ENV` 来区分环境：

- `DOCRADAR_ENV=test` - 测试环境（默认）
- `DOCRADAR_ENV=production` - 生产环境

可以通过以下方式设置环境变量：

**Windows命令行：**
```
set DOCRADAR_ENV=production
python app.py
```

**Linux/Mac终端：**
```
export DOCRADAR_ENV=production
python app.py
```

**Docker Compose：**
在docker-compose.yml文件中配置（已预先配置）

### 使用多环境Docker部署

更新后的`docker-compose.yml`已经同时配置了生产和测试两个环境的容器：

- **生产环境**：端口 5000，数据存储在 `./data/production/`
- **测试环境**：端口 5001，数据存储在 `./data/test/`

启动两个环境：
```
docker-compose up -d
```

只启动生产环境：
```
docker-compose up -d docradar
```

只启动测试环境：
```
docker-compose up -d docradar_test
```

## 快速启动指南

### 方式1：局域网部署

```bash
# 克隆或下载代码库
git clone [代码库地址]
cd DocRadar

# 创建虚拟环境并激活
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python init_db.py

# 启动应用（默认为测试环境）
python app.py

# 或指定为生产环境启动
# export DOCRADAR_ENV=production  # Linux/Mac
# set DOCRADAR_ENV=production     # Windows
# python app.py
```

访问：http://localhost:5000 或 http://服务器IP:5000

### 方式2：Docker部署（推荐）

```bash
# 克隆或下载代码库
git clone [代码库地址]
cd DocRadar

# 编辑docker-compose.yml（可选，修改配置）

# 构建并启动所有容器（同时启动测试和生产环境）
docker-compose up -d

# 或只启动生产环境
# docker-compose up -d docradar

# 或只启动测试环境
# docker-compose up -d docradar_test
```

访问：
- 生产环境：http://服务器IP:5000
- 测试环境：http://服务器IP:5001

### 方式3：云服务器部署

1. 在云服务器上执行方式1或方式2的部署步骤
2. 配置Nginx反向代理和SSL证书
3. 设置适当的防火墙规则

## 详细说明

有关各种部署方式的详细说明、配置参数和最佳实践，请参考[DEPLOYMENT.md](DEPLOYMENT.md)文档。

## 用户认证

首次启动系统时，会自动创建默认管理员账户：
- 用户名：admin
- 密码：随机生成（查看控制台输出）

**重要提示**：请在首次登录后立即修改默认密码！

## 问题排查

如果在部署过程中遇到问题，请：

1. 查看系统日志（位于tmp目录）
2. 检查[DEPLOYMENT.md](DEPLOYMENT.md)中的故障排除部分
3. 如需进一步帮助，请联系技术支持 