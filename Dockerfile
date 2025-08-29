# 使用官方 Python 基础镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /home/lynxhawk/policy_ai

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/home/lynxhawk/policy_ai

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制 requirements.txt 到临时位置安装依赖
COPY requirements.txt /tmp/requirements.txt

# 安装 Python 依赖
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# 不复制任何代码文件！代码通过 volume 挂载
# 不需要创建目录，挂载时 Docker 会自动处理
# 移除了: COPY . .

# 暴露端口
EXPOSE 8081 8082 8083 8084

# 默认命令（会被 docker-compose 覆盖）
CMD ["bash"]