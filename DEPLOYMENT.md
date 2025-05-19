# DocRadar Docker 部署指南

本文档提供了使用Docker部署DocRadar应用的详细步骤。

## 前置条件

- 安装 [Docker](https://docs.docker.com/get-docker/)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)

## 快速部署

### 1. 克隆或下载项目

```bash
git clone <项目仓库URL> docradar
cd docradar
```

### 2. 配置环境

修改`docker-compose.yml`文件中的环境变量：

```yaml
environment:
  - SECRET_KEY=change_this_to_a_secure_random_string  # 用于会话加密
  - ADMIN_KEY=change_this_to_a_secure_random_string   # 管理员API访问密钥
```

建议使用随机生成的字符串作为SECRET_KEY和ADMIN_KEY，可以使用以下命令生成：

```bash
# Linux/macOS
openssl rand -hex 32

# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

### 3. 创建必要的数据目录

```bash
mkdir -p data/uploads data/db data/logs
```

### 4. 构建并启动服务

```bash
docker-compose up -d
```

首次启动时会自动构建Docker镜像，这可能需要几分钟。

### 5. 访问应用

应用现在应该运行在 http://localhost:5000

首次登录时将使用系统生成的随机管理员密码，您可以通过查看Docker容器的日志获取此密码：

```bash
docker-compose logs docradar
```

找到类似以下的日志行：
```
创建默认管理员账户: admin / <随机密码>
```

登录后请立即修改密码。

## 配置选项

### 端口映射

如果您想更改应用的端口，请修改`docker-compose.yml`中的端口映射：

```yaml
ports:
  - "8080:5000"  # 将主机的8080端口映射到容器的5000端口
```

### 数据持久化

应用数据通过Docker卷映射到本地存储：

- `./data/uploads`: 存储上传的文档文件
- `./data/db`: 存储SQLite数据库文件
- `./data/logs`: 存储应用日志
- `./users.json`: 存储用户账号信息

### 调整工作进程数

可以通过修改`docker-compose.yml`中的命令调整Gunicorn工作进程数：

```yaml
command: gunicorn --workers=4 --bind 0.0.0.0:5000 app:app
```

对于大多数低到中等负载的部署，4个工作进程已经足够。

## 维护操作

### 查看日志

```bash
docker-compose logs -f docradar
```

### 重启服务

```bash
docker-compose restart docradar
```

### 停止服务

```bash
docker-compose down
```

### 更新应用

当有新版本发布时，您可以按照以下步骤更新：

```bash
git pull  # 获取最新代码
docker-compose down  # 停止当前服务
docker-compose build  # 重新构建镜像
docker-compose up -d  # 启动更新后的服务
```

## 高级配置

### 使用外部反向代理

在生产环境中，建议使用Nginx或Traefik等反向代理服务器，并配置HTTPS。

示例Nginx配置：

```nginx
server {
    listen 80;
    server_name docradar.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 安全建议

1. 更改默认管理员密码
2. 使用复杂的SECRET_KEY和ADMIN_KEY
3. 限制对Docker主机的访问
4. 在生产环境中配置HTTPS
5. 定期备份数据目录

## 故障排除

### 容器无法启动

检查日志以获取详细错误信息：

```bash
docker-compose logs docradar
```

### 无法上传文件

确保数据目录有正确的权限：

```bash
chmod -R 755 data
```

### 数据库错误

如果遇到数据库错误，可能需要检查数据库文件权限或手动初始化数据库：

```bash
docker-compose exec docradar python init_db.py
``` 