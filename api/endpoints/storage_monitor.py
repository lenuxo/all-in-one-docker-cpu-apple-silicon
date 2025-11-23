"""
存储监控端点
提供临时文件使用情况的监控和管理
"""

import os
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import structlog

from ..utils.memory_file_handler import memory_file_handler, cleanup_expired_files, schedule_cleanup

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

@router.get(
    "/temp-files/status",
    summary="获取临时文件状态",
    description="""
    获取当前临时文件的使用情况，包括文件数量、总大小等。

    ## 返回信息
    - 文件数量
    - 总大小
    - 平均文件大小
    - 最大文件大小
    """
)
async def get_temp_files_status() -> Dict[str, Any]:
    """获取临时文件状态"""
    try:
        file_count = memory_file_handler.get_file_count()
        total_size = memory_file_handler.get_total_size()

        # 计算平均和最大文件大小
        avg_size = total_size / file_count if file_count > 0 else 0
        max_size = 0

        for file_info in memory_file_handler.temp_files.values():
            try:
                if file_info["path"].exists():
                    file_size = file_info["path"].stat().st_size
                    max_size = max(max_size, file_size)
            except Exception:
                continue

        return {
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "average_size_bytes": int(avg_size),
            "average_size_mb": round(avg_size / (1024 * 1024), 2),
            "max_size_bytes": max_size,
            "max_size_mb": round(max_size / (1024 * 1024), 2),
            "temp_directory": os.path.join(os.getcwd(), "tmp", "music_analysis")
        }

    except Exception as e:
        logger.error("获取临时文件状态失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取状态失败")

@router.post(
    "/temp-files/cleanup",
    summary="清理临时文件",
    description="""
    手动触发临时文件清理。

    ## 清理策略
    - 立即清理所有临时文件
    - 安全删除，确保文件系统完整性
    - 返回清理统计信息
    """
)
async def cleanup_temp_files() -> Dict[str, Any]:
    """手动清理所有临时文件"""
    try:
        cleaned_count = await memory_file_handler.cleanup_all()

        # 触发系统级清理
        await schedule_cleanup()

        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"成功清理 {cleaned_count} 个临时文件"
        }

    except Exception as e:
        logger.error("手动清理临时文件失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

@router.post(
    "/temp-files/cleanup-expired",
    summary="清理过期文件",
    description="""
    清理超过指定时间的临时文件。

    ## 参数说明
    - max_age_minutes: 文件最大保存时间（分钟）
    - 默认: 30分钟
    """,
    responses={
        200: {
            "description": "清理完成",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "cleaned_count": 5,
                        "max_age_minutes": 30,
                        "message": "成功清理 5 个过期文件"
                    }
                }
            }
        }
    }
)
async def cleanup_expired_temp_files(max_age_minutes: int = 30) -> Dict[str, Any]:
    """清理过期临时文件"""
    try:
        if max_age_minutes <= 0:
            raise HTTPException(status_code=400, detail="max_age_minutes 必须大于 0")

        if max_age_minutes > 1440:  # 24小时
            raise HTTPException(status_code=400, detail="max_age_minutes 不能超过 24 小时")

        # 获取清理前的状态
        before_count = memory_file_handler.get_file_count()

        # 执行清理
        await cleanup_expired_files(max_age_minutes)

        # 获取清理后的状态
        after_count = memory_file_handler.get_file_count()
        cleaned_count = before_count - after_count

        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "max_age_minutes": max_age_minutes,
            "before_count": before_count,
            "after_count": after_count,
            "message": f"成功清理 {cleaned_count} 个超过 {max_age_minutes} 分钟的文件"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("清理过期文件失败", error=str(e), max_age_minutes=max_age_minutes)
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")