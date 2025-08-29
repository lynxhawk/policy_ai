# 使用官方 Python 基础镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install supervisor

# 复制应用代码
#COPY . .

# 暴露端口（这里列出所有可能用到的端口）
EXPOSE 8081 8082 8083 8084

# 默认命令（在 docker-compose 中会被覆盖）
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
