"""
系统监控API端点
提供系统状态、健康检查和监控功能
"""

import os
import time
import psutil
import platform
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
import structlog

from ..models import HealthResponse

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

# 应用启动时间
START_TIME = time.time()

# 统计计数器
stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_processed": 0,
    "active_tasks": 0
}

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="系统健康检查",
    description="""
    检查API服务的健康状态和系统资源使用情况。

    ## 返回信息
    - 服务状态和版本
    - 系统运行时间
    - CPU和内存使用率
    - 当前活跃任务数
    - 历史处理统计
    - 已加载的分析模型

    ## 监控用途
    - 负载均衡器健康检查
    - 系统监控和告警
    - 性能分析和优化
    - 容量规划
    """
)
async def health_check():
    """
    系统健康检查端点
    """
    try:
        # 获取系统信息
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 计算运行时间
        uptime_seconds = time.time() - START_TIME
        uptime_str = _format_uptime(uptime_seconds)

        # 获取已加载的模型（这里简化处理）
        models_loaded = ["harmonix-all"]  # 实际应用中可以动态检测

        # 检查服务状态
        status = "healthy"
        if cpu_usage > 90:
            status = "degraded"
        if memory.percent > 90:
            status = "degraded"
        if disk.percent > 95:
            status = "critical"

        return HealthResponse(
            status=status,
            version="1.0.0",
            uptime=uptime_str,
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            active_tasks=stats["active_tasks"],
            total_processed=stats["total_processed"],
            models_loaded=models_loaded
        )

    except Exception as e:
        logger.error("健康检查失败", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"健康检查失败: {str(e)}"
        )

@router.get(
    "/stats",
    summary="获取详细统计信息",
    description="""
    获取API服务的详细统计信息和性能指标。

    ## 统计指标
    - 请求统计（总数、成功率、失败率）
    - 处理统计（文件数量、处理时间）
    - 系统资源使用情况
    - 错误率分析
    """
)
async def get_statistics():
    """
    获取详细统计信息
    """
    try:
        # 系统信息
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_total": psutil.disk_usage('/').total
        }

        # 请求统计
        request_stats = {
            "total_requests": stats["total_requests"],
            "successful_requests": stats["successful_requests"],
            "failed_requests": stats["failed_requests"],
            "success_rate": (
                stats["successful_requests"] / max(stats["total_requests"], 1) * 100
            ),
            "failure_rate": (
                stats["failed_requests"] / max(stats["total_requests"], 1) * 100
            )
        }

        # 处理统计
        processing_stats = {
            "total_processed": stats["total_processed"],
            "active_tasks": stats["active_tasks"],
            "average_processing_time": None,  # 可以从实际处理数据计算
            "total_processing_time": None
        }

        # 资源使用情况
        current_time = datetime.now()
        resource_usage = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "memory_available": psutil.virtual_memory().available,
            "disk_free": psutil.disk_usage('/').free
        }

        return {
            "success": True,
            "timestamp": current_time.isoformat(),
            "uptime_seconds": time.time() - START_TIME,
            "system_info": system_info,
            "request_stats": request_stats,
            "processing_stats": processing_stats,
            "resource_usage": resource_usage
        }

    except Exception as e:
        logger.error("获取统计信息失败", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )

@router.get(
    "/version",
    summary="获取API版本信息",
    description="""
    获取API服务的版本信息和构建详情。

    ## 版本信息
    - API版本号
    - 构建时间
    - Git提交信息（如果可用）
    - 依赖库版本
    """
)
async def get_version():
    """
    获取版本信息
    """
    try:
        # 版本信息（可以是从环境变量或文件读取）
        version_info = {
            "api_version": "1.0.0",
            "build_date": "2024-11-23",
            "environment": os.getenv("ENV", "development"),
            "python_version": platform.python_version(),
            "platform": platform.platform()
        }

        # 依赖库版本（简化显示）
        dependencies = {
            "fastapi": "0.104.1",
            "allin1": "0.6.1"  # 从实际的allin1包获取
        }

        return {
            "success": True,
            "version": version_info["api_version"],
            "version_info": version_info,
            "dependencies": dependencies,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error("获取版本信息失败", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"获取版本信息失败: {str(e)}"
        )

def _format_uptime(seconds: float) -> str:
    """
    格式化运行时间

    Args:
        seconds: 秒数

    Returns:
        str: 格式化的运行时间
    """
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)

def increment_request_stats(success: bool = True):
    """
    更新请求统计

    Args:
        success: 请求是否成功
    """
    stats["total_requests"] += 1
    if success:
        stats["successful_requests"] += 1
    else:
        stats["failed_requests"] += 1

def increment_processed_stats():
    """
    更新处理统计
    """
    stats["total_processed"] += 1

def update_active_tasks(count: int):
    """
    更新活跃任务数

    Args:
        count: 活跃任务数量
    """
    stats["active_tasks"] = count