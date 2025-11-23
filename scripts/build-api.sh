#!/bin/bash

# 音乐分析API构建脚本 (推荐)
# 构建现代化的RESTful API服务
# 专为Mac M系列芯片（Apple Silicon）优化

set -e

# 配置变量
IMAGE_NAME="music-analysis-api"
TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    log_success "Docker检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p api/storage/{uploads,results,temp}
    chmod 755 api/storage/{uploads,results,temp}
    log_success "目录创建完成"
}

# 构建Docker镜像
build_image() {
    log_info "开始构建API服务镜像: ${FULL_IMAGE_NAME}"

    # 确保在正确的目录
    if [ ! -f "api/Dockerfile" ]; then
        log_error "未找到 api/Dockerfile，请在项目根目录运行此脚本"
        exit 1
    fi

    # 构建镜像
    docker build \
        -f api/Dockerfile \
        -t "${FULL_IMAGE_NAME}" \
        --progress=plain \
        .

    if [ $? -eq 0 ]; then
        log_success "Docker镜像构建成功: ${FULL_IMAGE_NAME}"
    else
        log_error "Docker镜像构建失败"
        exit 1
    fi
}

# 显示镜像信息
show_image_info() {
    log_info "镜像信息:"
    docker images "${IMAGE_NAME}:${TAG}"
}

# 运行测试
run_test() {
    log_info "运行容器测试..."

    # 启动容器
    docker run -d \
        --name "${IMAGE_NAME}-test" \
        -p 8000:8000 \
        -e ENV=development \
        "${FULL_IMAGE_NAME}"

    # 等待容器启动
    log_info "等待容器启动..."
    sleep 30

    # 健康检查
    if curl -f http://localhost:8000/api/system/health > /dev/null 2>&1; then
        log_success "容器测试通过，API服务正常运行"
        log_info "API文档地址: http://localhost:8000/docs"
        log_info "API健康检查: http://localhost:8000/api/system/health"
    else
        log_error "容器测试失败，API服务未正常启动"
        docker logs "${IMAGE_NAME}-test"
    fi

    # 停止并删除测试容器
    docker stop "${IMAGE_NAME}-test" > /dev/null 2>&1 || true
    docker rm "${IMAGE_NAME}-test" > /dev/null 2>&1 || true
}

# 清理函数
cleanup() {
    log_info "清理临时资源..."
    docker rm -f "${IMAGE_NAME}-test" > /dev/null 2>&1 || true
    log_success "清理完成"
}

# 主函数
main() {
    log_info "🎵 音乐分析API构建脚本"
    log_info "================================"

    # 设置错误处理
    trap cleanup EXIT

    # 执行步骤
    check_docker
    create_directories
    build_image
    show_image_info

    # 询问是否运行测试
    echo
    read -p "是否要运行容器测试？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_test
    else
        log_info "跳过测试"
    fi

    log_success "构建完成！"
    log_info ""
    log_info "🚀 使用方法:"
    log_info "  启动服务: docker run -p 8000:8000 ${FULL_IMAGE_NAME}"
    log_info "  查看日志: docker logs <container-id>"
    log_info "  访问文档: http://localhost:8000/docs"
    log_info ""
    log_info "🐳 使用Docker Compose (推荐):"
    log_info "  开发环境: docker-compose up --build"
    log_info "  生产环境: docker-compose --profile production up -d"
}

# 执行主函数
main "$@"