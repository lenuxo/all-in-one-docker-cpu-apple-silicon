"""
分析进度查询端点
提供单文件和批量分析进度查询功能
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import structlog

from ..services.progress_tracker import ProgressTracker, ProgressManager

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

@router.get(
    "/progress/{request_id}",
    summary="查询单文件分析进度",
    description="""
    查询单个音频文件分析的实时进度。

    ## 返回信息
    - 当前分析步骤
    - 步骤描述
    - 步骤进度（0-100%）
    - 总体进度（0-100%）
    - 已用时间
    - 预计剩余时间
    - 开始时间

    ## 分析步骤说明
    1. **initializing** - 初始化分析环境（1-2秒）
    2. **loading_model** - 加载深度学习模型（5-15秒）
    3. **audio_separation** - 音轨分离处理（10-30秒）
    4. **spectrogram_extraction** - 提取频谱图特征（5-15秒）
    5. **feature_extraction** - 提取音频特征（3-8秒）
    6. **beat_tracking** - 节拍检测分析（5-12秒）
    7. **segment_analysis** - 音乐段落分析（8-20秒）
    8. **generating_results** - 生成分析结果（2-5秒）
    9. **saving_outputs** - 保存输出文件（1-3秒）
    10. **completed** - 分析完成

    ## 使用示例
    ```javascript
    // 轮询进度
    const pollProgress = async (requestId) => {
        const response = await fetch(`/api/progress/${requestId}`);
        const data = await response.json();

        console.log(`当前步骤: ${data.step_description}`);
        console.log(`总体进度: ${data.overall_progress}%`);
        console.log(`预计剩余: ${data.estimated_remaining}`);

        if (data.overall_progress < 100) {
            setTimeout(() => pollProgress(requestId), 1000);
        }
    };
    ```
    """,
    responses={
        200: {
            "description": "查询成功",
            "content": {
                "application/json": {
                    "example": {
                        "request_id": "req_20241123_001",
                        "current_step": "beat_tracking",
                        "step_description": "节拍检测分析",
                        "step_progress": 65.0,
                        "overall_progress": 68.5,
                        "elapsed_time": 45.2,
                        "estimated_remaining": "1分30秒",
                        "step_start_time": 1699123456.789
                    }
                }
            }
        },
        404: {
            "description": "请求不存在或已过期",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "进度信息不存在，请求ID可能无效或已过期"
                    }
                }
            }
        }
    }
)
async def get_analysis_progress(request_id: str) -> Dict[str, Any]:
    """
    获取单文件分析进度

    Args:
        request_id: 请求ID

    Returns:
        Dict: 进度信息
    """
    tracker = ProgressTracker.get_tracker(request_id)

    if tracker is None:
        raise HTTPException(
            status_code=404,
            detail="进度信息不存在，请求ID可能无效或已过期"
        )

    return tracker.get_status()

@router.get(
    "/progress/summary",
    summary="获取所有分析进度摘要",
    description="""
    获取当前所有活跃分析任务的进度统计信息。

    ## 返回信息
    - 活跃任务总数
    - 各步骤的任务数量分布
    - 平均进度
    - 各任务的简要信息

    ## 适合场景
    - 系统监控面板
    - 负载均衡决策
    - 性能分析
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "total_active": 3,
                        "by_step": {
                            "audio_separation": 1,
                            "beat_tracking": 1,
                            "segment_analysis": 1
                        },
                        "average_progress": 72.3,
                        "active_tasks": [
                            {
                                "request_id": "req_20241123_001",
                                "current_step": "audio_separation",
                                "overall_progress": 25.0,
                                "elapsed_time": 18.5
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_progress_summary(include_details: bool = False) -> Dict[str, Any]:
    """
    获取所有分析任务的进度摘要

    Args:
        include_details: 是否包含详细任务信息

    Returns:
        Dict: 进度摘要
    """
    try:
        # 获取基础统计信息
        summary = ProgressManager.get_progress_summary()

        if include_details:
            # 添加详细任务信息
            all_progress = ProgressManager.get_all_active_progress()
            summary["active_tasks"] = [
                {
                    "request_id": request_id,
                    "current_step": data["current_step"],
                    "step_description": data["step_description"],
                    "overall_progress": data["overall_progress"],
                    "elapsed_time": data["elapsed_time"],
                    "estimated_remaining": data.get("estimated_remaining")
                }
                for request_id, data in all_progress.items()
            ]

        logger.info(
            "进度摘要查询",
            total_active=summary["total_active"],
            average_progress=summary.get("average_progress", 0)
        )

        return summary

    except Exception as e:
        logger.error("获取进度摘要失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取进度摘要失败: {str(e)}")

@router.delete(
    "/progress/{request_id}",
    summary="清除进度信息",
    description="""
    手动清除指定请求的进度信息。

    ## 使用场景
    - 分析完成后清理跟踪器
    - 释放内存资源
    - 强制停止跟踪
    """
)
async def clear_progress(request_id: str) -> Dict[str, str]:
    """
    清除指定请求的进度信息

    Args:
        request_id: 请求ID

    Returns:
        Dict: 操作结果
    """
    success = ProgressTracker.remove_tracker(request_id)

    if success:
        logger.info("进度信息已清除", request_id=request_id)
        return {"success": True, "message": f"进度信息已清除: {request_id}"}
    else:
        logger.warning("进度信息不存在，无法清除", request_id=request_id)
        raise HTTPException(
            status_code=404,
            detail=f"进度信息不存在: {request_id}"
        )

@router.post(
    "/progress/cleanup",
    summary="清理过期进度信息",
    description="""
    清理超过指定时间的进度跟踪器。

    ## 参数说明
    - max_age_hours: 最大保存时间（小时），默认24小时

    ## 自动清理
    系统会定期自动清理过期的进度信息，此接口用于手动触发清理。
    """
)
async def cleanup_expired_progress(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    清理过期的进度信息

    Args:
        max_age_hours: 最大保存时间（小时）

    Returns:
        Dict: 清理结果
    """
    if max_age_hours <= 0:
        raise HTTPException(status_code=400, detail="max_age_hours 必须大于 0")

    if max_age_hours > 168:  # 7天
        raise HTTPException(status_code=400, detail="max_age_hours 不能超过 7 天")

    try:
        cleaned_count = ProgressTracker.cleanup_expired(max_age_hours)

        logger.info(
            "过期进度清理完成",
            cleaned_count=cleaned_count,
            max_age_hours=max_age_hours
        )

        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "max_age_hours": max_age_hours,
            "message": f"已清理 {cleaned_count} 个过期的进度跟踪器"
        }

    except Exception as e:
        logger.error("清理过期进度失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")