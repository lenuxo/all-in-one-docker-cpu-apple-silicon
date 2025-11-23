# 音乐分析API Docker镜像
# 基于原有的allin1镜像，添加FastAPI Web服务

# 使用Python 3.8基础镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    ffmpeg \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip

# 复制并安装过滤后的依赖
COPY requirements_filtered.txt .
COPY api/requirements.txt api/requirements.txt

# 安装torch和依赖（CPU版本）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir torch==2.2.2 torchvision torchaudio==2.2.2 cython
RUN pip install --no-cache-dir -r requirements_filtered.txt
RUN pip install madmom==0.16.1

# 安装NATTEN（CPU版本）
RUN pip install natten==0.15.0

# 安装Web服务依赖
RUN pip install --no-cache-dir -r api/requirements.txt

# 复制整个项目代码
COPY . .

# 安装allin1项目（开发模式）
RUN pip install -e .

# 创建API服务所需的目录
RUN mkdir -p api/static/uploads \
    && mkdir -p api/static/results \
    && mkdir -p api/temp \
    && chmod 755 api/static/uploads \
    && chmod 755 api/static/results \
    && chmod 755 api/temp

# 创建非root用户（安全最佳实践）
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/system/health || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]