# CLI工具Docker镜像 (v1.0 - 传统版本)
# 注意：推荐使用API服务版本 ./api/Dockerfile
# 专为Mac M系列芯片（Apple Silicon）优化

# 使用Python 3.8基础镜像（ARM64架构）
FROM python:3.8-slim

# Set the working directory to /app
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y cmake build-essential
RUN pip install --upgrade pip

# Copy the requirements.txt file
#COPY requirements.txt .
COPY requirements_filtered.txt .

# 安装torch和依赖（Apple Silicon优化版本）
# Torch 2.2.2 for Apple Silicon
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir torch==2.2.2 torchvision torchaudio==2.2.2 cython

# 安装其他依赖
RUN pip install --no-cache-dir -r requirements_filtered.txt
RUN pip install madmom==0.16.1

# 安装NATTEN（Apple Silicon兼容版本）
RUN pip install natten==0.15.0

# Copy the entire project to the /app directory
COPY . .

# Install the project in editable mode
RUN pip install -e .

# WARNING each execution downloads the demucs model again
# Downloading: "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th" to /root/.cache/torch/hub/checkpoints/955717e8-8726e21a.th

# Set the entrypoint to run the allin1 command
ENTRYPOINT ["python", "-m", "allin1.cli"]
