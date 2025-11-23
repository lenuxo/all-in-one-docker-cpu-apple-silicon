"""
异步音频分析端点
提供带进度跟踪的音频分析API，适合需要实时反馈的交互式应用
"""

import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
import structlog

from ..models import (
    AnalysisRequest,
    AsyncAnalysisSubmitResponse,
    AsyncTaskStatus,
    AsyncAnalysisResult,
    ErrorResponse,
    ModelType,
    DeviceType
)
from ..services.analysis_service import AnalysisService
from ..utils import (
    validate_audio_file,
    get_audio_duration
)
from ..utils.memory_file_handler import memory_file_handler
from ..services.progress_tracker import ProgressTracker, AnalysisStep

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

# 初始化分析服务
analysis_service = AnalysisService()

# 任务状态存储
async_tasks: Dict[str, Dict[str, Any]] = {}


@router.post(
    "/analyze/async",
    response_model=AsyncAnalysisSubmitResponse,
    responses={
        200: {
            "description": "异步分析任务创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "分析任务已创建",
                        "task_id": "task_20241123_001",
                        "request_id": "req_20241123_001",
                        "estimated_time": "45-90秒",
                        "status_url": "/api/analyze/task/task_20241123_001/status"
                    }
                }
            }
        },
        400: {"description": "请求参数错误", "model": ErrorResponse},
        413: {"description": "文件过大", "model": ErrorResponse},
        422: {"description": "文件格式不支持", "model": ErrorResponse}
    },
    summary="异步分析音频文件",
    description="""
    **异步音频分析API - 提交任务后轮询状态获取结果**

    ## 🎯 使用场景
    - **Web应用**: 需要进度条显示的用户界面
    - **移动应用**: 提供良好的用户体验
    - **长时间分析**: 大文件或复杂处理
    - **多任务并行**: 同时处理多个文件

    ## 📋 使用流程
    1. **提交任务**: 调用此接口创建分析任务
    2. **轮询状态**: 使用返回的status_url查询任务状态
    3. **获取结果**: 任务完成后调用任务结果接口

    ## 📝 API调用示例
    ```bash
    # 1. 提交分析任务
    curl -X POST "http://localhost:8193/api/analyze/async" \\
      -F "file=@song.wav" \\
      -F "model=harmonix-all" \\
      -F "visualize=true"

    # 响应示例
    {
      "success": true,
      "message": "分析任务已创建",
      "task_id": "task_20241123_001",
      "request_id": "req_20241123_001",
      "estimated_time": "45-90秒",
      "status_url": "/api/analyze/task/task_20241123_001/status"
    }
    ```

    ## ⏱️ 预估处理时间
    - **小文件** (< 1分钟): 30-60秒
    - **中等文件** (1-3分钟): 60-120秒
    - **大文件** (3-10分钟): 120-300秒

    ## 🔗 相关接口
    - `[GET] /api/analyze/task/{task_id}/status` - 查询任务状态
    - `[GET] /api/analyze/task/{task_id}/result` - 获取分析结果
    """,
    deprecated=False
)
async def submit_analysis_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ...,
        description="""
        ## 音频文件

        ### 支持格式
        - **WAV**: 强烈推荐，无压缩，分析精度最高
        - **MP3**: 支持，但可能有20-40ms时差

        ### 文件要求
        - **大小**: 由核心库和系统资源决定
        - **时长**: 由核心库和系统资源决定
        - **质量**: 建议采样率44.1kHz或更高
        """
    ),
    model: ModelType = Form(
        default=ModelType.HARMONIX_ALL,
        description="""
        ## 分析模型

        **harmonix-all**: 集成8个模型的平均结果（推荐，精度最高）
        **harmonix-fold0-7**: 单个折模型（速度更快，精度略低）
        """
    ),
    visualize: bool = Form(
        default=False,
        description="是否生成可视化图表 (PDF格式)"
    ),
    sonify: bool = Form(
        default=False,
        description="是否生成音频化标注 (WAV格式)"
    ),
    include_activations: bool = Form(
        default=False,
        description="是否包含原始激活数据"
    ),
    include_embeddings: bool = Form(
        default=False,
        description="是否包含嵌入向量数据"
    ),
    overwrite: bool = Form(
        default=False,
        description="是否覆盖已存在的分析结果"
    )
) -> AsyncAnalysisSubmitResponse:
    """
    提交异步音频分析任务

    创建后台任务，返回任务ID和状态查询URL。
    客户端需要轮询状态接口来跟踪分析进度。
    """
    task_id = f"task_{time.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    request_id = str(uuid.uuid4())
    start_time = time.time()
    file_id = None

    try:
        logger.info(
            "提交异步分析任务",
            task_id=task_id,
            request_id=request_id,
            filename=file.filename,
            model=model.value
        )

        # 验证文件
        is_valid, error_msg = await validate_audio_file(file)
        if not is_valid:
            raise HTTPException(status_code=422, detail=error_msg)

        # 保存文件到临时目录
        upload_path, file_id = await memory_file_handler.save_to_temp(file)

        # 获取音频时长信息（用于显示，不做限制）
        duration = await get_audio_duration(upload_path)
        if duration:
            logger.info("音频时长信息", duration=duration, filename=file.filename)

        # 创建分析请求（强制使用CPU）
        analysis_request = AnalysisRequest(
            model=model,
            device=DeviceType.CPU,  # 强制使用CPU
            visualize=visualize,
            sonify=sonify,
            include_activations=include_activations,
            include_embeddings=include_embeddings,
            overwrite=overwrite
        )

        # 估算处理时间
        if duration:
            estimated_time = f"{int(duration * 3)}-{int(duration * 6)}秒"
        else:
            estimated_time = "60-120秒"

        # 保存任务信息
        async_tasks[task_id] = {
            "task_id": task_id,
            "request_id": request_id,
            "file_path": upload_path,
            "file_id": file_id,
            "request": analysis_request,
            "status": "pending",
            "progress": 0.0,
            "current_step": "queued",
            "message": "任务已创建，等待处理",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "estimated_time": estimated_time,
            "duration": duration,
            "start_time": None,
            "end_time": None
        }

        # 添加后台任务
        background_tasks.add_task(
            _process_async_analysis_task,
            task_id
        )

        logger.info(
            "异步分析任务已创建",
            task_id=task_id,
            request_id=request_id,
            estimated_time=estimated_time
        )

        return AsyncAnalysisSubmitResponse(
            success=True,
            message="分析任务已创建",
            task_id=task_id,
            request_id=request_id,
            estimated_time=estimated_time,
            status_url=f"/api/analyze/task/{task_id}/status"
        )

    except Exception as e:
        # 清理临时文件
        if file_id:
            await memory_file_handler.cleanup_file(file_id)

        logger.error("创建异步分析任务失败", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get(
    "/analyze/task/{task_id}/status",
    response_model=AsyncTaskStatus,
    responses={
        200: {
            "description": "成功获取任务状态",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "task_20241123_001",
                        "request_id": "req_20241123_001",
                        "status": "processing",
                        "progress": 65.5,
                        "current_step": "beat_tracking",
                        "message": "正在进行节拍检测分析",
                        "created_at": "2024-11-23T10:30:00Z",
                        "updated_at": "2024-11-23T10:31:15Z",
                        "estimated_remaining": "20-30秒"
                    }
                }
            }
        },
        404: {"description": "任务不存在", "model": ErrorResponse}
    },
    summary="查询异步分析任务状态",
    description="""
    **查询异步分析任务的实时状态和进度**

    ## 📊 返回信息
    - **任务状态**: pending/processing/completed/failed
    - **进度百分比**: 0-100的完成进度
    - **当前步骤**: 具体的分析步骤名称
    - **状态消息**: 人类可读的状态描述
    - **预计剩余时间**: 基于当前进度的估算

    ## 🔄 轮询策略
    - **建议间隔**: 1-2秒轮询一次
    - **completed状态**: 任务完成，可调用结果接口
    - **failed状态**: 任务失败，检查error字段

    ## 📝 调用示例
    ```bash
    curl -X GET "http://localhost:8193/api/analyze/task/task_20241123_001/status"
    ```

    ## 🔗 相关接口
    - `[POST] /api/analyze/async` - 提交分析任务
    - `[GET] /api/analyze/task/{task_id}/result` - 获取分析结果
    """
)
async def get_task_status(task_id: str) -> AsyncTaskStatus:
    """
    获取异步分析任务的当前状态

    Args:
        task_id: 任务ID

    Returns:
        AsyncTaskStatus: 任务状态信息
    """
    if task_id not in async_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )

    task_info = async_tasks[task_id]

    # 计算预估剩余时间
    estimated_remaining = None
    if task_info["status"] == "processing" and task_info["progress"] > 0:
        elapsed = time.time() - task_info.get("start_time", time.time())
        total_estimated = elapsed / (task_info["progress"] / 100)
        remaining = total_estimated - elapsed
        if remaining > 0:
            estimated_remaining = f"{int(remaining)}秒"

    return AsyncTaskStatus(
        task_id=task_info["task_id"],
        request_id=task_info["request_id"],
        status=task_info["status"],
        progress=task_info["progress"],
        current_step=task_info["current_step"],
        message=task_info["message"],
        created_at=task_info["created_at"],
        updated_at=task_info["updated_at"],
        estimated_remaining=estimated_remaining,
        error=task_info.get("error")
    )


@router.get(
    "/analyze/task/{task_id}/result",
    response_model=AsyncAnalysisResult,
    responses={
        200: {
            "description": "成功获取分析结果",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "分析完成",
                        "data": {
                            "path": "/tmp/uploads/song.wav",
                            "bpm": 120.5,
                            "beats": [0.33, 0.75, 1.14, 1.56],
                            "downbeats": [0.33, 1.94, 3.53],
                            "beat_positions": [1, 2, 3, 4, 1, 2, 3, 4],
                            "segments": [
                                {"start": 0.0, "end": 0.33, "label": "start"},
                                {"start": 0.33, "end": 13.13, "label": "intro"},
                                {"start": 13.13, "end": 37.53, "label": "chorus"}
                            ]
                        },
                        "files": {
                            "json_result": "/api/download/result_song.json",
                            "visualization": "/api/download/viz_song.pdf"
                        },
                        "processing_time": 30.5,
                        "model_used": "harmonix-all",
                        "request_id": "req_20241123_001",
                        "task_id": "task_20241123_001"
                    }
                }
            }
        },
        400: {"description": "任务未完成", "model": ErrorResponse},
        404: {"description": "任务不存在", "model": ErrorResponse}
    },
    summary="获取异步分析任务结果",
    description="""
    **获取已完成异步分析任务的结果数据**

    ## ⚠️ 重要说明
    - **仅限完成状态**: 只能获取status为completed的任务结果
    - **数据格式**: 与同步分析API返回格式完全一致
    - **失败任务**: 失败任务请调用status接口查看错误信息

    ## 📊 返回数据结构
    - **data**: 音乐分析结果（BPM、节拍、段落等）
    - **files**: 生成的文件下载链接
    - **processing_time**: 实际处理耗时
    - **model_used**: 使用的分析模型

    ## 📝 调用示例
    ```bash
    # 1. 先检查任务状态
    curl -X GET "http://localhost:8193/api/analyze/task/task_20241123_001/status"

    # 2. 状态为completed时获取结果
    curl -X GET "http://localhost:8193/api/analyze/task/task_20241123_001/result"
    ```

    ## 🔗 相关接口
    - `[POST] /api/analyze/async` - 提交分析任务
    - `[GET] /api/analyze/task/{task_id}/status` - 查询任务状态
    """
)
async def get_task_result(task_id: str) -> AsyncAnalysisResult:
    """
    获取已完成异步分析任务的结果

    Args:
        task_id: 任务ID

    Returns:
        AsyncAnalysisResult: 分析结果（格式与同步分析一致）
    """
    if task_id not in async_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )

    task_info = async_tasks[task_id]

    if task_info["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务未完成或失败，当前状态: {task_info['status']}。请先调用 /api/analyze/task/{task_id}/status 查看状态"
        )

    if "result" not in task_info:
        raise HTTPException(
            status_code=500,
            detail="任务已完成但结果数据丢失"
        )

    result_data = task_info["result"]
    processing_time = task_info.get("end_time", time.time()) - task_info.get("start_time", time.time())

    return AsyncAnalysisResult(
        success=True,
        message="分析完成",
        data=result_data["data"],
        files=result_data.get("files"),
        processing_time=processing_time,
        model_used=task_info["request"].model.value,
        request_id=task_info["request_id"],
        task_id=task_id
    )


@router.delete(
    "/analyze/task/{task_id}",
    responses={
        200: {
            "description": "任务删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "任务已删除: task_20241123_001"
                    }
                }
            }
        },
        400: {"description": "无法删除正在处理的任务", "model": ErrorResponse},
        404: {"description": "任务不存在", "model": ErrorResponse}
    },
    summary="删除异步分析任务",
    description="""
    **删除异步分析任务及其相关数据**

    ## ⚠️ 删除限制
    - **completed**: 可以删除已完成任务
    - **failed**: 可以删除失败任务
    - **processing**: 无法删除正在处理的任务
    - **pending**: 可以删除排队中的任务

    ## 📝 调用示例
    ```bash
    curl -X DELETE "http://localhost:8193/api/analyze/task/task_20241123_001"
    ```
    """
)
async def delete_task(task_id: str) -> Dict[str, str]:
    """
    删除异步分析任务

    Args:
        task_id: 任务ID

    Returns:
        Dict: 操作结果
    """
    if task_id not in async_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )

    task_info = async_tasks[task_id]

    if task_info["status"] == "processing":
        raise HTTPException(
            status_code=400,
            detail="正在处理的任务无法删除，请等待完成后删除"
        )

    # 删除任务记录
    del async_tasks[task_id]

    logger.info("异步分析任务已删除", task_id=task_id)

    return {
        "success": True,
        "message": f"任务已删除: {task_id}"
    }


async def _process_async_analysis_task(task_id: str):
    """
    处理异步分析任务（后台运行）

    Args:
        task_id: 任务ID
    """
    if task_id not in async_tasks:
        return

    task_info = async_tasks[task_id]
    request_id = task_info["request_id"]

    try:
        # 更新任务状态为处理中
        task_info["status"] = "processing"
        task_info["progress"] = 5.0
        task_info["current_step"] = "initializing"
        task_info["message"] = "开始分析处理"
        task_info["start_time"] = time.time()
        task_info["updated_at"] = datetime.utcnow().isoformat() + "Z"

        file_path = task_info["file_path"]
        request = task_info["request"]

        # 执行分析
        result_data, file_links = await analysis_service.analyze_single_file_with_progress(
            file_path,
            request,
            request_id,
            lambda step, progress, message: _update_task_progress(task_id, step, progress, message)
        )

        # 保存结果
        task_info["status"] = "completed"
        task_info["progress"] = 100.0
        task_info["current_step"] = "completed"
        task_info["message"] = "分析完成"
        task_info["end_time"] = time.time()
        task_info["updated_at"] = datetime.utcnow().isoformat() + "Z"
        task_info["result"] = {
            "data": result_data,
            "files": file_links
        }

        logger.info(
            "异步分析任务完成",
            task_id=task_id,
            request_id=request_id,
            total_time=task_info["end_time"] - task_info["start_time"]
        )

    except Exception as e:
        # 更新任务状态为失败
        task_info["status"] = "failed"
        task_info["current_step"] = "failed"
        task_info["message"] = f"分析失败: {str(e)}"
        task_info["end_time"] = time.time()
        task_info["updated_at"] = datetime.utcnow().isoformat() + "Z"
        task_info["error"] = str(e)

        logger.error(
            "异步分析任务失败",
            task_id=task_id,
            request_id=request_id,
            error=str(e)
        )

    finally:
        # 清理临时文件
        file_id = task_info.get("file_id")
        if file_id:
            await memory_file_handler.cleanup_file(file_id)


def _update_task_progress(task_id: str, step: AnalysisStep, progress: float, message: str):
    """
    更新任务进度

    Args:
        task_id: 任务ID
        step: 分析步骤
        progress: 进度百分比
        message: 进度消息
    """
    if task_id in async_tasks:
        task_info = async_tasks[task_id]
        task_info["progress"] = progress
        task_info["current_step"] = step.value if hasattr(step, 'value') else str(step)
        task_info["message"] = message
        task_info["updated_at"] = datetime.utcnow().isoformat() + "Z"