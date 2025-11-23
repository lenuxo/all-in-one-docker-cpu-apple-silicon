"""
同步音频分析端点
提供简单、直接的音频分析API，适合快速集成和简单场景
"""

import time
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import structlog

from ..models import (
    AnalysisResponse,
    ErrorResponse,
    ModelType,
    DeviceType,
    AnalysisRequest
)
from ..services.analysis_service import AnalysisService
from ..utils import (
    validate_audio_file,
    get_audio_duration
)
from ..utils.memory_file_handler import memory_file_handler

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

# 初始化分析服务
analysis_service = AnalysisService()

@router.post(
    "/analyze/sync",
    response_model=AnalysisResponse,
    responses={
        200: {
            "description": "同步分析成功",
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
                            "visualization": "/api/download/viz_song.pdf",
                            "json_result": "/api/download/result_song.json"
                        },
                        "processing_time": 45.2,
                        "model_used": "harmonix-all",
                        "request_id": "req_20241123_001"
                    }
                }
            }
        },
        400: {"description": "请求参数错误", "model": ErrorResponse},
        408: {"description": "请求超时", "model": ErrorResponse},
        413: {"description": "文件过大", "model": ErrorResponse},
        422: {"description": "文件格式不支持", "model": ErrorResponse},
        504: {"description": "分析超时", "model": ErrorResponse}
    },
    summary="同步分析音频文件",
    description="""
    **同步音频分析API - 一次调用直接返回分析结果**

    ## 🎯 特点
    - **简单直接**: 一次HTTP调用完成所有分析流程
    - **自动超时**: 内置超时机制，防止请求无限等待
    - **无需轮询**: 不需要额外状态查询，结果直接返回
    - **快速集成**: 最简单的API调用方式

    ## 📋 适用场景
    - **脚本自动化**: 批量文件处理，后台定时任务
    - **快速原型**: 开发测试，概念验证
    - **简单应用**: 不需要进度显示的工具类应用
    - **单次分析**: 偶尔使用的分析需求

    ## ⏱️ 处理时间参考
    - **小文件** (< 1分钟): 30-60秒
    - **中等文件** (1-3分钟): 60-120秒
    - **大文件** (3-10分钟): 120-300秒

    ## ⏰ 超时设置
    - **默认超时**: 600秒（10分钟）
    - **可调范围**: 1-600秒
    - **超时处理**: 返回504错误，建议调整超时时间或文件大小

    ## 📝 使用示例

    ### 基础调用
    ```bash
    curl -X POST "http://localhost:8193/api/analyze/sync" \\
      -F "file=@song.wav" \\
      -F "model=harmonix-all"
    ```

    ### 完整参数调用
    ```bash
    curl -X POST "http://localhost:8193/api/analyze/sync" \\
      -F "file=@song.wav" \\
      -F "model=harmonix-all" \\
      -F "visualize=true" \\
      -F "sonify=true" \\
      -F "include_activations=true" \\
      -F "include_embeddings=true" \\
      -F "overwrite=true" \\
      -F "timeout=300"
    ```

    ### 响应示例
    ```json
    {
      "success": true,
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
        "visualization": "/api/download/viz_song.pdf",
        "json_result": "/api/download/result_song.json"
      },
      "processing_time": 45.2,
      "model_used": "harmonix-all",
      "request_id": "req_20241123_001"
    }
    ```

    ## 🔄 API对比

    | 特性 | 同步API | 异步API |
    |------|---------|---------|
    | **调用方式** | 一次调用返回结果 | 提交任务+轮询状态 |
    | **实现复杂度** | 简单 | 中等 |
    | **用户体验** | 需要等待 | 有进度反馈 |
    | **超时处理** | 自动处理 | 需要手动处理 |
    | **适用场景** | 脚本、后台任务 | Web应用、移动端 |
    | **资源占用** | 阻塞式 | 非阻塞式 |

    ## ⚠️ 重要注意事项
    - **客户端超时**: 确保客户端超时时间大于分析预估时间
    - **文件限制**: 文件大小和时长由核心库和系统资源决定
    - **批量处理**: 大量文件建议使用异步或批量API
    - **CPU模式**: 系统自动使用CPU进行分析，无需指定设备

    ## 🔗 相关接口
    - `[POST] /api/analyze/async` - 异步分析（带进度反馈）
    - `[POST] /api/analyze/batch` - 批量分析
    - `[GET] /api/analyze/info` - 获取分析服务信息
    """,
    deprecated=False
)
async def analyze_audio_sync(
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
    ),
    timeout: int = Form(
        default=600,
        description="分析超时时间（秒），最大600秒"
    )
) -> AnalysisResponse:
    """
    同步分析单个音频文件

    这个接口会阻塞直到分析完成，然后直接返回结果。
    适合简单的集成场景，不需要实时进度反馈。
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    file_id = None

    try:
        logger.info(
            "开始同步音频分析",
            request_id=request_id,
            filename=file.filename,
            model=model.value,
            device="cpu",
            timeout=timeout
        )

        # 验证超时参数
        if timeout <= 0 or timeout > 600:
            raise HTTPException(
                status_code=400,
                detail="timeout 必须在 1-600 秒之间"
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

        # 执行同步分析（带超时控制）
        import asyncio

        try:
            result_data, file_links = await asyncio.wait_for(
                analysis_service.analyze_single_file_with_progress(
                    upload_path,
                    analysis_request,
                    request_id
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            await memory_file_handler.cleanup_file(file_id)
            raise HTTPException(
                status_code=504,
                detail=f"分析超时（{timeout}秒），请尝试减少文件大小或增加超时时间"
            )

        processing_time = time.time() - start_time

        # 立即清理临时文件
        await memory_file_handler.cleanup_file(file_id)

        logger.info(
            "同步音频分析完成",
            request_id=request_id,
            processing_time=processing_time,
            duration=duration
        )

        return AnalysisResponse(
            success=True,
            message="分析完成",
            data=result_data,
            files=file_links,
            processing_time=processing_time,
            model_used=model.value,
            request_id=request_id
        )

    except HTTPException:
        # 确保异常情况下也清理临时文件
        if file_id:
            await memory_file_handler.cleanup_file(file_id)
        raise
    except Exception as e:
        # 确保异常情况下也清理临时文件
        if file_id:
            await memory_file_handler.cleanup_file(file_id)

        logger.error("同步分析失败", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"分析过程中发生错误: {str(e)}"
        )

@router.get(
    "/analyze/info",
    summary="获取分析服务信息",
    description="""
    获取音频分析服务的配置信息和预估时间。

    ## 返回信息
    - 支持的模型列表
    - 各模型的预估处理时间
    - 文件大小和时长限制
    - 系统当前负载

    ## 使用场景
    - 客户端显示分析选项
    - 提供用户友好的时间预估
    - 系统状态检查
    """
)
async def get_analysis_info() -> dict:
    """获取分析服务信息"""
    try:
        # 获取系统状态（这里可以集成更详细的监控）
        info = {
            "service": "音乐分析API",
            "version": "1.0.0",
            "models": {
                "harmonix-all": {
                    "description": "集成8个模型的平均结果（最高精度）",
                    "estimated_time": {
                        "small_file": "30-60秒",
                        "medium_file": "60-120秒",
                        "large_file": "120-300秒"
                    },
                    "recommended": True
                },
                "harmonix-fold0": {
                    "description": "第0折模型（单模型，速度更快）",
                    "estimated_time": {
                        "small_file": "20-40秒",
                        "medium_file": "40-80秒",
                        "large_file": "80-200秒"
                    },
                    "recommended": False
                }
            },
            "limitations": {
                "max_file_size": "50MB",
                "max_audio_duration": "10分钟",
                "max_concurrent_requests": 5,
                "sync_timeout_range": "1-600秒"
            },
            "supported_formats": {
                "wav": {
                    "name": "WAV",
                    "description": "推荐格式，无压缩，分析精度最高",
                    "recommended": True
                },
                "mp3": {
                    "name": "MP3",
                    "description": "支持格式，但可能有20-40ms时差",
                    "recommended": False
                }
            },
            "features": {
                "beat_tracking": True,
                "segment_analysis": True,
                "visualization": True,
                "sonification": True,
                "activations": True,
                "embeddings": True
            }
        }

        return info

    except Exception as e:
        logger.error("获取分析信息失败", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"获取服务信息失败: {str(e)}"
        )