#!/bin/bash

# 🎵 音乐分析 API 一键启动脚本
# All-In-One Music Structure Analyzer API Launcher
# 作者: Claude Code Assistant

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
SERVICE_NAME="music-analysis-api"
API_PORT=8193
HEALTH_CHECK_URL="http://localhost:$API_PORT/api/system/health"

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] $message${NC}"
}

print_success() {
    print_message "$GREEN" "✅ $1"
}

print_error() {
    print_message "$RED" "❌ $1"
}

print_warning() {
    print_message "$YELLOW" "⚠️  $1"
}

print_info() {
    print_message "$BLUE" "ℹ️  $1"
}

print_header() {
    echo -e "${PURPLE}"
    echo "🎵 ╔══════════════════════════════════════════════════════════════╗"
    echo "   ║        音乐分析 API 一键启动脚本                           ║"
    echo "   ║     All-In-One Music Structure Analyzer API              ║"
    echo "   ║                                                          ║"
    echo "   ║  🚀 快速启动  📊 健康检查  📚 API 文档                    ║"
    echo "   ╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查系统依赖
check_dependencies() {
    print_info "检查系统依赖..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        print_info "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        print_info "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi

    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker 服务未运行，请启动 Docker"
        print_info "macOS: 打开 Docker Desktop"
        print_info "Linux: sudo systemctl start docker"
        exit 1
    fi

    print_success "系统依赖检查通过"
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 $API_PORT 已被占用"
        print_info "尝试停止现有服务..."

        # 尝试优雅停止现有容器
        if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
            docker-compose -f "$COMPOSE_FILE" down
            sleep 5
        fi

        # 再次检查端口
        if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_error "端口 $API_PORT 仍被占用，请手动处理"
            exit 1
        fi
    fi
}

# 启动服务
start_service() {
    print_info "启动音乐分析 API 服务..."

    # 构建并启动服务
    if docker-compose -f "$COMPOSE_FILE" up --build -d; then
        print_success "服务启动命令执行成功"
    else
        print_error "服务启动失败"
        exit 1
    fi
}

# 等待服务健康检查
wait_for_service() {
    print_info "等待服务启动..."

    local max_attempts=60
    local attempt=1
    local wait_time=5

    while [ $attempt -le $max_attempts ]; do
        print_info "健康检查尝试 $attempt/$max_attempts..."

        if curl -s -f "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            print_success "服务已就绪！"
            return 0
        fi

        # 检查容器状态
        if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
            print_error "容器未运行，请检查日志"
            docker-compose -f "$COMPOSE_FILE" logs --tail=20
            exit 1
        fi

        sleep $wait_time
        attempt=$((attempt + 1))
    done

    print_error "服务启动超时，请检查日志"
    docker-compose -f "$COMPOSE_FILE" logs --tail=50
    exit 1
}

# 显示服务信息
show_service_info() {
    print_success "🎉 音乐分析 API 启动成功！"
    echo ""
    echo -e "${CYAN}📋 服务信息:${NC}"
    echo "   🌐 API 地址: http://localhost:$API_PORT"
    echo "   📚 API 文档: http://localhost:$API_PORT/docs"
    echo "   🔍 ReDoc 文档: http://localhost:$API_PORT/redoc"
    echo "   ❤️  健康检查: http://localhost:$API_PORT/api/system/health"
    echo ""

    # 获取实际的健康状态
    print_info "获取服务状态..."
    if health_status=$(curl -s "$HEALTH_CHECK_URL" 2>/dev/null); then
        echo -e "${CYAN}📊 服务状态:${NC}"
        echo "$health_status" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"   状态: {data['status']}\")
    print(f\"   版本: {data['version']}\")
    print(f\"   运行时间: {data['uptime']}\")
    print(f\"   CPU 使用率: {data['cpu_usage']}%\")
    print(f\"   内存使用率: {data['memory_usage']}%\")
    print(f\"   已加载模型: {', '.join(data['models_loaded'])}\")
except:
    print('   状态获取失败')
"
    else
        print_warning "无法获取详细状态信息"
    fi

    echo ""
    echo -e "${CYAN}🔧 管理命令:${NC}"
    echo "   查看日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo "   停止服务: docker-compose -f $COMPOSE_FILE down"
    echo "   重启服务: docker-compose -f $COMPOSE_FILE restart"
    echo "   查看状态: docker-compose -f $COMPOSE_FILE ps"
    echo ""
    echo -e "${CYAN}📝 API 使用示例:${NC}"
    echo "   健康检查: curl http://localhost:$API_PORT/api/system/health"
    echo "   分析音频: curl -X POST -F 'file=@your_audio.wav' http://localhost:$API_PORT/api/analysis/analyze"
    echo ""
    print_success "现在可以开始使用音乐分析 API 了！"
}

# 显示使用帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -q, --quiet    静默模式，减少输出"
    echo "  -c, --check    仅检查依赖，不启动服务"
    echo "  -s, --stop     停止服务"
    echo "  -r, --restart  重启服务"
    echo "  -l, --logs     查看服务日志"
    echo ""
    echo "示例:"
    echo "  $0                # 启动服务"
    echo "  $0 --stop         # 停止服务"
    echo "  $0 --restart      # 重启服务"
    echo "  $0 --logs         # 查看日志"
    echo "  $0 --check        # 检查依赖"
}

# 停止服务
stop_service() {
    print_info "停止音乐分析 API 服务..."
    if docker-compose -f "$COMPOSE_FILE" down; then
        print_success "服务已停止"
    else
        print_error "停止服务失败"
        exit 1
    fi
}

# 重启服务
restart_service() {
    print_info "重启音乐分析 API 服务..."
    stop_service
    sleep 2
    start_service
    wait_for_service
    show_service_info
}

# 查看日志
show_logs() {
    print_info "显示服务日志..."
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# 仅检查依赖
check_only() {
    print_header
    check_dependencies
    check_port
    print_success "所有检查通过，可以启动服务"
}

# 清理函数
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "脚本执行失败"
    fi
}

# 设置退出时的清理
trap cleanup EXIT

# 主函数
main() {
    # 解析命令行参数
    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        -q|--quiet)
            # 静默模式 - 这里可以设置一个变量来控制输出
            shift
            ;;
        -c|--check)
            check_only
            exit 0
            ;;
        -s|--stop)
            stop_service
            exit 0
            ;;
        -r|--restart)
            restart_service
            exit 0
            ;;
        -l|--logs)
            show_logs
            exit 0
            ;;
        "")
            # 默认启动服务
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac

    # 默认行为：启动服务
    print_header
    check_dependencies
    check_port
    start_service
    wait_for_service
    show_service_info
}

# 运行主函数
main "$@"