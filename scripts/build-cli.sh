#!/bin/bash

# 传统CLI工具构建脚本 (备用)
# 构建原始的命令行工具镜像

set -e

echo "🔨 构建传统CLI工具镜像"
echo "注意: 推荐使用API服务，运行: ./scripts/build-api.sh"
echo ""

# 构建原始CLI镜像
docker build -t allinone -f ./Dockerfile .

if [ $? -eq 0 ]; then
    echo "✅ CLI镜像构建成功: allinone"
    echo ""
    echo "📋 CLI使用方法:"
    echo "  docker run -it \\"
    echo "     -v \$PWD/audio:/app/input \\"
    echo "     -v \$PWD/results:/app/output \\"
    echo "     allinone --out-dir /app/output/analysis /app/input/your-file.wav"
    echo ""
    echo "🆕 推荐使用API服务:"
    echo "  ./scripts/build-api.sh"
    echo "  或者: docker-compose up --build"
    echo ""
    echo "📚 详细文档:"
    echo "  API文档: API_README.md"
    echo "  主文档: README.md"
else
    echo "❌ CLI镜像构建失败"
    exit 1
fi