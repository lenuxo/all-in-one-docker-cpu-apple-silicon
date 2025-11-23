"""
音频分析API端点
处理音频文件分析相关的请求
"""

import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import structlog

from ..models import (
    AnalysisRequest,
    AnalysisResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    ErrorResponse,
    ModelType,
    DeviceType
)
from ..services.analysis_service import AnalysisService
from ..utils import (
    validate_audio_file,
    get_file_info,
    generate_unique_filename,
    cleanup_temp_files,
    ensure_directory,
    get_audio_duration
)
from ..utils.memory_file_handler import memory_file_handler, cleanup_expired_files

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

# 初始化分析服务
analysis_service = AnalysisService()

# 文件存储路径
UPLOAD_DIR = Path("api/static/uploads")
RESULTS_DIR = Path("api/static/results")
TEMP_DIR = Path("api/temp")

@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        200: {
            "description": "分析成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "分析完成",
                        "data": {
                            "path": "/tmp/uploads/song.wav",
                            "bpm": 120.0,
                            "beats": [0.33, 0.75, 1.14],
                            "segments": [
                                {"start": 0.0, "end": 13.13, "label": "intro"},
                                {"start": 13.13, "end": 37.53, "label": "chorus"}
                            ]
                        },
                        "processing_time": 15.23,
                        "model_used": "harmonix-all",
                        "request_id": "req_20241123_001"
                    }
                }
            }
        },
        400: {"description": "请求参数错误", "model": ErrorResponse},
        413: {"description": "文件过大", "model": ErrorResponse},
        422: {"description": "文件格式不支持", "model": ErrorResponse}
    },
    summary="分析单个音频文件",
    description="""
    ## 功能说明

    对上传的音频文件进行音乐结构分析，包括：
    - 节拍检测（BPM、节拍位置、强拍）
    - 段落分析（边界检测和标签分类）
    - 可选的可视化和音频化生成

    ## 支持格式

    - **WAV**: 推荐格式，精度最高
    - **MP3**: 支持格式，可能有20-40ms时差

    ## 处理时间

    - 单个文件：10-60秒（取决于文件长度和设备性能）
    - 最大文件大小：50MB
    - 最大时长：10分钟

    ## 使用示例

    ```bash
    curl -X POST "http://localhost:8193/api/analyze" \\
      -H "Content-Type: multipart/form-data" \\
      -F "file=@song.wav" \\
      -F "model=harmonix-all" \\
      -F "visualize=true"
    ```
    """
)
async def analyze_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ...,
        description="""
        ## 音频文件

        ### 支持格式
        - **WAV**: 强烈推荐，无压缩，分析精度最高
        - **MP3**: 支持，但可能有20-40ms时差

        ### 文件要求
        - 最大大小：50MB
        - 最大时长：10分钟
        - 采样率：建议44.1kHz或更高

        ### 注意事项
        - MP3文件因解码器差异可能有时差
        - 建议先用FFmpeg转换为WAV格式以获得最佳精度

        ### 示例文件结构
        ```
        song.wav (音频文件)
        ├── 采样率: 44100 Hz
        ├── 声道: 立体声
        ├── 位深: 16-bit
        └── 时长: 3:45
        ```
        """,
        example="song.wav"
    ),
    model: ModelType = Form(
        default=ModelType.HARMONIX_ALL,
        description="""
        ## 分析模型选择

        ### 可用模型

        | 模型名称 | 描述 | 精度 | 速度 |
        |---------|------|------|------|
        | `harmonix-all` | 集成8个模型的平均结果 | 最高 | 最慢 |
        | `harmonix-fold0` | 单一模型 | 高 | 快 |
        | `harmonix-fold1` | 单一模型 | 高 | 快 |

        ### 推荐使用
        - **生产环境**: `harmonix-all`（最高精度）
        - **快速测试**: `harmonix-fold0`（快速响应）
        """,
        example="harmonix-all"
    ),
    device: DeviceType = Form(
        default=DeviceType.CPU,
        description="""
        ## 计算设备

        ### 选项
        - `cpu`: CPU计算（兼容性最好）
        - `cuda`: GPU加速（需要CUDA支持）

        ### 性能对比
        - CPU: 约30-60秒/歌曲
        - GPU: 约10-20秒/歌曲

        ### 注意事项
        CUDA设备需要在Docker中正确配置NVIDIA运行时
        """,
        example="cpu"
    ),
    visualize: bool = Form(
        default=False,
        description="""
        ## 生成可视化图表

        生成的PDF包含：
        - 波形图
        - 节拍标记
        - 段落边界和标签
        - 节拍位置图

        输出格式：PDF文件
        文件大小：约100-500KB
        """,
        example=True
    ),
    sonify: bool = Form(
        default=False,
        description="""
        ## 生成音频化文件

        在原音频基础上添加：
        - 节拍点击声（木鱼声）
        - 强拍强调声
        - 段落边界提示音

        输出格式：WAV文件
        采样率：44.1kHz
        声道：立体声
        """,
        example=False
    ),
    include_activations: bool = Form(
        default=False,
        description="""
        ## 原始激活数据

        包含模型的原始输出：
        - beat: 节拍激活概率 (100 FPS)
        - downbeat: 强拍激活概率 (100 FPS)
        - segment: 段落边界激活概率 (100 FPS)
        - label: 段落标签概率分布 (10类 × 100 FPS)

        用途：高级分析、自定义后处理
        格式：NPZ文件
        """,
        example=False
    ),
    include_embeddings: bool = Form(
        default=False,
        description="""
        ## 嵌入向量数据

        包含音频的特征表示：
        - 维度：[4个声源 × 时间步 × 24维特征]
        - 声源：bass, drums, other, vocals
        - 时间分辨率：100 FPS (0.01秒/帧)

        用途：机器学习、相似性分析
        格式：NPY文件
        """,
        example=False
    ),
    overwrite: bool = Form(
        default=False,
        description="""
        ## 覆盖已存在的结果

        如果设置为True，将重新分析文件并覆盖之前的结果。
        如果设置为False，发现已有结果时直接返回缓存。

        建议在首次分析时设为False，需要更新时设为True。
        """,
        example=False
    )
) -> AnalysisResponse:
    """
    分析单个音频文件

    上传音频文件并返回音乐结构分析结果
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    file_id = None  # 初始化文件ID变量

    try:
        # 验证文件
        is_valid, error_msg = await validate_audio_file(file)
        if not is_valid:
            raise HTTPException(status_code=422, detail=error_msg)

        # 保存文件到内存临时目录
        upload_path, file_id = await memory_file_handler.save_to_temp(file)

        logger.info(
            "文件上传成功（内存模式）",
            request_id=request_id,
            filename=file.filename,
            file_id=file_id,
            temp_path=str(upload_path)
        )

        # 获取音频时长信息（用于显示，不做限制）
        duration = await get_audio_duration(upload_path)
        if duration:
            logger.info("音频时长信息", duration=duration, filename=file.filename)

        # 创建分析请求参数
        analysis_request = AnalysisRequest(
            model=model,
            device=device,
            visualize=visualize,
            sonify=sonify,
            include_activations=include_activations,
            include_embeddings=include_embeddings,
            overwrite=overwrite
        )

        # 执行分析
        result_data, file_links = await analysis_service.analyze_single_file(
            upload_path,
            analysis_request,
            request_id
        )

        processing_time = time.time() - start_time

        # 立即清理临时文件（分析完成后）
        await memory_file_handler.cleanup_file(file_id)

        # 添加定期清理任务（清理过期文件）
        background_tasks.add_task(cleanup_expired_files, max_age_minutes=30)

        logger.info(
            "分析完成",
            request_id=request_id,
            processing_time=processing_time,
            model=model.value
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
        raise
    except Exception as e:
        # 确保在异常情况下也清理临时文件
        if file_id:
            await memory_file_handler.cleanup_file(file_id)

        logger.error("分析失败", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"分析过程中发生错误: {str(e)}"
        )


@router.post(
    "/analyze-batch",
    response_model=BatchAnalysisResponse,
    summary="批量分析音频文件",
    description="""
    批量分析多个音频文件。上传多个音频文件，返回任务ID用于查询结果。

    ## 适合场景
    - 需要分析大量音频文件
    - 不需要立即获得结果
    - 处理时间较长的任务

    ## 处理流程
    1. 上传文件，创建批量任务
    2. 后台排队处理
    3. 通过任务ID查询进度和结果
    """
)
async def analyze_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(
        ...,
        description="要分析的音频文件列表，最多支持20个文件",
        min_items=1,
        max_items=20
    ),
    model: ModelType = Form(default=ModelType.HARMONIX_ALL),
    device: DeviceType = Form(default=DeviceType.CPU),
    visualize: bool = Form(default=True),
    sonify: bool = Form(default=False),
    include_activations: bool = Form(default=False),
    include_embeddings: bool = Form(default=False),
    overwrite: bool = Form(default=False),
    priority: int = Form(default=1, ge=1, le=5, description="任务优先级（1-5）")
) -> BatchAnalysisResponse:
    """
    批量分析多个音频文件
    """
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="至少需要上传一个文件")

    # 验证所有文件
    invalid_files = []
    for i, file in enumerate(files):
        is_valid, error_msg = await validate_audio_file(file)
        if not is_valid:
            invalid_files.append(f"文件{i+1}({file.filename}): {error_msg}")

    if invalid_files:
        raise HTTPException(
            status_code=422,
            detail=f"文件验证失败: {'; '.join(invalid_files)}"
        )

    # 创建批量分析任务
    batch_request = BatchAnalysisRequest(
        model=model,
        device=device,
        visualize=visualize,
        sonify=sonify,
        include_activations=include_activations,
        include_embeddings=include_embeddings,
        overwrite=overwrite,
        priority=priority
    )

    task_id = await analysis_service.create_batch_task(
        files, batch_request, background_tasks
    )

    return BatchAnalysisResponse(
        success=True,
        task_id=task_id,
        message=f"批量分析任务已创建，共{len(files)}个文件",
        estimated_time=f"{len(files) * 30}-{len(files) * 60}秒",
        file_count=len(files),
        priority=priority
    )


@router.get(
    "/analyze-batch/{task_id}",
    summary="查询批量分析任务状态",
    description="""
    查询批量分析任务的执行状态和结果。

    ## 返回信息
    - 任务状态（pending/processing/completed/failed）
    - 处理进度（0-100%）
    - 已完成和失败的文件列表
    - 完整的分析结果（如果任务已完成）
    """
)
async def get_batch_analysis_status(task_id: str):
    """
    获取批量分析任务的状态和结果
    """
    result = await analysis_service.get_batch_task_status(task_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )

    return result


@router.delete(
    "/analyze-batch/{task_id}",
    summary="取消批量分析任务",
    description="取消正在执行或排队中的批量分析任务"
)
async def cancel_batch_analysis(task_id: str):
    """
    取消批量分析任务
    """
    success = await analysis_service.cancel_batch_task(task_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在或无法取消: {task_id}"
        )

    return {"success": True, "message": f"任务已取消: {task_id}"}


@router.get(
    "/models",
    summary="获取可用模型列表",
    description="获取所有可用的分析模型及其详细信息"
)
async def get_available_models():
    """
    获取可用的分析模型列表
    """
    models = []
    for model in ModelType:
        models.append({
            "name": model.value,
            "description": model.get_description(),
            "type": "ensemble" if model == ModelType.HARMONIX_ALL else "single_model"
        })

    return {
        "success": True,
        "models": models,
        "default": ModelType.HARMONIX_ALL.value
    }