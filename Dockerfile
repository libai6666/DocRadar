FROM python:3.9-slim

WORKDIR /app

# 安装依赖（先复制requirements.txt提高缓存效率）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    # 安装Magic库（用于文件类型检测）
    apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 复制应用代码
COPY . .

# 确保目录存在
RUN mkdir -p static/uploads static/doc_images tmp

# 暴露端口
EXPOSE 5000

# 运行应用
CMD ["python", "app.py"] 