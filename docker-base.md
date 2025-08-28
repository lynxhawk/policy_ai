# Docker

## 配置代理&登录

```
#设置系统代理
export HTTP_PROXY=http://proxy_server:port
export HTTPS_PROXY=http://proxy_server:port
export http_proxy=http://proxy_server:port
export https_proxy=http://proxy_server:port
	
# 验证设置
env | grep -i proxy

# 登录Docker Hub
docker login
```

## 安装Docker
```
# 更新系统
sudo dnf update -y
	
# 安装必要工具
sudo dnf install -y yum-utils device-mapper-persistent-data lvm2

# 添加 Docker 官方仓库
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
	
# 检查可用的 Docker 版本
dnf list docker-ce --showduplicates | sort -r
	
# 安装最新版本的 Docker
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## 启动&验证

### 启动Docker
```
# 启动 Docker
sudo systemctl start docker
	
# 设置开机自启
sudo systemctl enable docker
	
# 检查状态
sudo systemctl status docker
```

### 验证安装

```
# 测试 Docker
sudo docker --version

sudo docker run hello-world

# 查看 Docker 系统信息
docker info
```

#### 将用户添加到 docker 组（避免每次都用 sudo）

```
sudo usermod -aG docker $USER
newgrp docker
```

##构建单个镜像和容器

### 构建单个镜像
```
# 在项目根目录创建 Dockerfile

# 构建镜像
docker build -t my-app:latest .

# 指定 Dockerfile 路径
docker build -f path/to/Dockerfile -t my-app:latest .

# 查看镜像列表
docker images

# 删除镜像
docker rmi my-app:latest
```

### 运行单个容器
```
# 运行容器
docker run -d --name my-container -p 8080:8080 my-app:latest

# 交互式运行
docker run -it --name my-container my-app:latest /bin/bash

# 后台运行并映射端口
docker run -d -p 8080:8080 --name my-container my-app:latest

# 挂载数据卷
docker run -d -v /host/path:/container/path --name my-container my-app:latest
```

### 常用命令
```
# 查看运行中的容器
docker ps

# 查看所有容器
docker ps -a

# 停止容器
docker stop my-container

# 启动容器
docker start my-container

# 重启容器
docker restart my-container

# 删除容器
docker rm my-container

# 查看容器日志
docker logs my-container

# 进入容器
docker exec -it my-container /bin/bash
```

## Docker Compose（统一管理多个容器和服务）

### 构建镜像&容器
 - 打开项目根目录

 - 创建`Dockerfile`

 - 创建`docker-compose.yml`
 *添加  restart: unless-stopped 维持服务启动状态*

 - 创建`.dockerignore`

 - 构建并启动服务 `docker-compose up --build`

### 常用命令
```
# 启动服务
docker compose up

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs
```

### Dockerfile(参考)
```
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

# 复制应用代码
COPY . .

# 暴露端口（这里列出所有可能用到的端口）
EXPOSE 8081 8082 8083 8084

# 默认命令（在 docker-compose 中会被覆盖）
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### docker-compose.yml(参考)
```
services:
  service1:
    image: my_app:latest
    container_name: service1_container
    ports:
      - "8084:8000"
    volumes:
      - .:/app  # 挂载当前目录到容器的 /app
    working_dir: /app
    environment:
      - SERVICE_NAME=service1_container
      - PYTHONPATH=/app
    command: ["python", "-m", "uvicorn", "service1:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    restart: unless-stopped
    networks:
      - app-network

  service2:
    image: my_app:latest
    container_name: service2_container
    ports:
      - "8083:8000"
    volumes:
      - .:/app  # 挂载当前目录到容器的 /app
    working_dir: /app
    environment:
      - SERVICE_NAME=service2_container
      - PYTHONPATH=/app
    command: ["python", "-m", "uvicorn", "service2:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    restart: unless-stopped
    networks:
      - app-network

  service3:
    image: my_app:latest
    container_name: service3_container
    ports:
      - "8082:8000"
    volumes:
      - .:/app  # 挂载当前目录到容器的 /app
    working_dir: /app
    environment:
      - SERVICE_NAME=service3_container
      - PYTHONPATH=/app
    command: ["python", "-m", "uvicorn", "service3:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    restart: unless-stopped
    networks:
      - app-network

  service4:
    image: my_app:latest
    container_name: service4_container
    ports:
      - "8081:8000"
    volumes:
      - .:/app  # 挂载当前目录到容器的 /app
    working_dir: /app
    environment:
      - SERVICE_NAME=service4_container
      - PYTHONPATH=/app
    command: ["python", "-m", "uvicorn", "service4:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```