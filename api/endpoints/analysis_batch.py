"""
批量音频分析端点
提供多文件批量处理功能，支持任务管理和详细进度跟踪
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
import structlog

from ..models import (
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    TaskStatus,
    ErrorResponse,
    ModelType
)
from ..services.analysis_service import AnalysisService
from ..utils import validate_audio_file, get_audio_duration
from ..utils.memory_file_handler import memory_file_handler

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

# 初始化分析服务
analysis_service = AnalysisService()

# 批量任务存储
batch_tasks: Dict[str, Dict[str, Any]] = {}

@router.post(
    "/analyze/batch",
    response_model=BatchAnalysisResponse,
    responses={
        200: {
            "description": "批量分析任务创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "task_id": "batch_20241123_001",
                        "message": "批量分析任务已创建，共5个文件",
                        "estimated_time": "5-10分钟",
                        "file_count": 5,
                        "priority": 1,
                        "files": [
                            {"filename": "song1.wav", "size": "15.2MB", "status": "valid"},
                            {"filename": "song2.mp3", "size": "8.7MB", "status": "valid"}
                        ]
                    }
                }
            }
        },
        400: {"description": "请求参数错误", "model": ErrorResponse},
        413: {"description": "文件过大", "model": ErrorResponse},
        422: {"description": "文件格式不支持", "model": ErrorResponse}
    },
    summary="批量分析音频文件",
    description="""
    **批量处理多个音频文件，支持详细的任务管理和进度跟踪**

    ## 特点
    - 📁 **多文件并行处理**
    - 🎯 **详细的任务管理**
    - 📊 **实时进度跟踪**
    - 🔧 **灵活的优先级设置**
    - 💾 **智能资源管理**

    ## 使用场景
    - **批量处理**: 处理大量音频文件
    - **自动化流程**: 集成到自动化工作流
    - **用户上传**: 支持用户一次上传多个文件
    - **定时任务**: 定期批量分析音频

    ## 工作流程

    ### 1. 提交批量任务
    ```bash
    curl -X POST "http://localhost:8193/api/analyze/batch" \\
      -F "files=@song1.wav" \\
      -F "files=@song2.mp3" \\
      -F "model=harmonix-all" \\
      -F "priority=1"
    ```

    ### 2. 查询任务状态
    ```bash
    curl -X GET "http://localhost:8193/api/analyze/batch/{task_id}/status"
    ```

    ### 3. 获取批量结果
    ```bash
    curl -X GET "http://localhost:8193/api/analyze/batch/{task_id}/result"
    ```

    ## 文件验证

    ### 支持格式
    - **WAV**: 推荐格式，无压缩，分析精度最高
    - **MP3**: 支持格式，但可能有20-40ms时差

    ### 文件限制
    - **单个文件**: 由核心库和系统资源决定
    - **音频时长**: 由核心库和系统资源决定
    - **批量数量**: 单次最多50个文件

    ### 验证结果
    - **valid**: 文件通过验证
    - **invalid_format**: 不支持的格式
    - **too_large**: 文件过大
    - **too_long**: 音频时长超限

    ## 优先级设置

    | 优先级 | 处理顺序 | 适用场景 |
    |--------|----------|----------|
    | 1 | 高优先级 | 紧急任务、VIP用户 |
    | 2 | 正常优先级 | 常规任务（默认） |
    | 3 | 低优先级 | 后台批量任务 |

    ## 任务状态说明

    - **pending**: 任务排队中，等待处理
    - **processing**: 正在处理文件
    - **completed**: 所有文件处理完成
    - **failed**: 处理过程中出现错误
    - **cancelled**: 任务被用户取消

    ## 进度信息示例
    ```json
    {
      "task_id": "batch_20241123_001",
      "status": "processing",
      "progress": 60.0,
      "current_file": "song3.wav",
      "completed_files": ["song1.wav", "song2.wav"],
      "failed_files": [],
      "estimated_remaining": "2-3分钟",
      "file_count": 5,
      "completed_count": 2,
      "failed_count": 0
    }
    ```

    ## 错误处理

    ### 单个文件失败
    - 继续处理其他文件
    - 在结果中标记失败文件和原因
    - 不影响整个批量任务

    ### 整个任务失败
    - 系统级错误
    - 所有文件都无法处理
    - 任务状态标记为failed

    ## 最佳实践

    ### 1. 文件组织
    - 建议将相似类型的音频文件放在同一批次
    - 避免混用不同质量参数的文件

    ### 2. 资源管理
    - 根据服务器性能设置合理的批次大小
    - 高峰期使用较低优先级

    ### 3. 监控和告警
    - 定期检查任务状态
    - 设置失败率告警阈值
    - 监控系统资源使用情况

    ## 客户端集成示例

    ### JavaScript 前端
    ```javascript
    // 提交批量任务
    const submitBatchTask = async (files, options = {}) => {
      const formData = new FormData();

      files.forEach(file => {
        formData.append('files', file);
      });

      formData.append('model', options.model || 'harmonix-all');
      formData.append('priority', options.priority || 2);

      const response = await fetch('/api/analyze/batch', {
        method: 'POST',
        body: formData
      });

      return await response.json();
    };

    // 监控批量任务进度
    const monitorBatchProgress = async (taskId, onUpdate) => {
      const checkStatus = async () => {
        const response = await fetch(`/api/analyze/batch/${taskId}/status`);
        const status = await response.json();

        onUpdate(status);

        if (status.status === 'processing') {
          setTimeout(checkStatus, 2000); // 每2秒检查一次
        }

        return status;
      };

      return await checkStatus();
    };

    // 获取批量结果
    const getBatchResult = async (taskId) => {
      const response = await fetch(`/api/analyze/batch/${taskId}/result`);
      return await response.json();
    };
    ```

    ## 性能优化

    ### 并行处理
    - 根据系统资源调整并发数量
    - 避免过度并行导致资源竞争

    ### 内存管理
    - 及时清理临时文件
    - 监控内存使用情况

    ### 缓存策略
    - 缓存模型加载结果
    - 重用频谱图计算结果
    """,
    deprecated=False
)
async def submit_batch_analysis(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(
        ...,
        description="""
        ## 音频文件列表

        支持1-50个文件同时上传。

        ### 文件要求
        - **格式**: WAV (推荐) 或 MP3
        - **大小**: 每个文件由核心库和系统资源决定
        - **时长**: 每个文件由核心库和系统资源决定
        - **数量**: 单次最多50个文件
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
    priority: int = Form(
        default=2,
        description="""
        ## 任务优先级

        **1**: 高优先级（紧急任务）
        **2**: 正常优先级（默认）
        **3**: 低优先级（后台任务）
        """
    ),
    visualize: bool = Form(
        default=False,
        description="是否为所有文件生成可视化图表"
    ),
    sonify: bool = Form(
        default=False,
        description="是否为所有文件生成音频化标注"
    ),
    include_activations: bool = Form(
        default=False,
        description="是否包含所有文件的原始激活数据"
    ),
    include_embeddings: bool = Form(
        default=False,
        description="是否包含所有文件的嵌入向量数据"
    ),
    overwrite: bool = Form(
        default=False,
        description="是否覆盖已存在的分析结果"
    ),
    continue_on_error: bool = Form(
        default=True,
        description="单个文件失败时是否继续处理其他文件"
    )
) -> BatchAnalysisResponse:
    """
    提交批量音频分析任务

    创建批量处理任务，支持多文件并行分析。
    返回任务ID和详细的文件验证信息。
    """
    # 生成任务ID
    task_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    try:
        # 验证文件数量
        if len(files) == 0:
            raise HTTPException(status_code=400, detail="至少需要上传一个文件")

        if len(files) > 50:
            raise HTTPException(status_code=400, detail="单次最多支持50个文件")

        # 验证优先级
        if priority not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="priority 必须是 1、2 或 3")

        # 强制使用CPU设备，忽略请求中的device参数
        device = "cpu"
        logger.info(
            "提交批量分析任务",
            task_id=task_id,
            file_count=len(files),
            model=model.value,
            device=device,
            priority=priority
        )

        # 验证所有文件
        validated_files = []
        total_size = 0
        invalid_files = []

        for i, file in enumerate(files):
            try:
                # 基础验证
                is_valid, error_msg = await validate_audio_file(file)

                file_info = {
                    "filename": file.filename,
                    "original_index": i,
                    "status": "valid",
                    "error": None
                }

                if not is_valid:
                    file_info["status"] = f"invalid_{error_msg.split(':')[0].lower()}"
                    file_info["error"] = error_msg
                    invalid_files.append(file_info)
                    continue

                # 获取文件大小信息
                content = await file.read()
                file_size = len(content)
                await file.seek(0)  # 重置文件指针

                file_info["size_bytes"] = file_size
                file_info["size_mb"] = round(file_size / (1024 * 1024), 2)
                total_size += file_size

                validated_files.append(file_info)

            except Exception as e:
                file_info = {
                    "filename": file.filename,
                    "original_index": i,
                    "status": "validation_error",
                    "error": f"文件验证失败: {str(e)}"
                }
                invalid_files.append(file_info)

        # 检查是否有有效文件
        if len(validified_files) == 0:
            raise HTTPException(
                status_code=400,
                detail="没有有效的音频文件，请检查文件格式和大小"
            )

        # 估算处理时间（假设每个文件平均处理时间）
        avg_time_per_file = 30  # CPU平均处理时间（秒）
        estimated_seconds = len(validated_files) * avg_time_per_file
        estimated_time = f"{estimated_seconds//60}-{estimated_seconds//60 + 1}分钟"

        # 保存文件到临时目录
        temp_file_paths = []
        file_ids = []

        for file_info in validated_files:
            original_file = files[file_info["original_index"]]

            # 保存文件
            upload_path, file_id = await memory_file_handler.save_to_temp(original_file)

            # 获取音频时长信息（用于显示，不做限制）
            duration = await get_audio_duration(upload_path)
            if duration:
                logger.info("音频时长信息", duration=duration, filename=original_file.filename)
                file_info["duration"] = duration

            temp_file_paths.append(upload_path)
            file_ids.append(file_id)
            file_info["temp_path"] = str(upload_path)
            file_info["file_id"] = file_id
            file_info["duration"] = duration

        # 重新计算有效文件数量
        valid_files = [f for f in validated_files if f["status"] == "valid"]

        if len(valid_files) == 0:
            raise HTTPException(
                status_code=400,
                detail="没有符合要求的音频文件（时长超过限制）"
            )

        # 创建批量任务记录
        batch_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "priority": priority,
            "file_count": len(valid_files),
            "valid_files": valid_files,
            "invalid_files": invalid_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "temp_file_paths": temp_file_paths,
            "file_ids": file_ids,
            "request": {
                "model": model,
                "device": device,
                "visualize": visualize,
                "sonify": sonify,
                "include_activations": include_activations,
                "include_embeddings": include_embeddings,
                "overwrite": overwrite,
                "continue_on_error": continue_on_error
            },
            "progress": {
                "current_file": None,
                "completed_files": [],
                "failed_files": [],
                "results": {},
                "completed_count": 0,
                "failed_count": 0
            },
            "timing": {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None
            },
            "estimated_time": estimated_time
        }

        # 添加后台任务
        background_tasks.add_task(
            _process_batch_analysis_task,
            task_id
        )

        logger.info(
            "批量分析任务已创建",
            task_id=task_id,
            valid_files=len(valid_files),
            invalid_files=len(invalid_files),
            total_size_mb=batch_tasks[task_id]["total_size_mb"],
            estimated_time=estimated_time
        )

        return BatchAnalysisResponse(
            success=True,
            task_id=task_id,
            message=f"批量分析任务已创建，共{len(valid_files)}个文件",
            estimated_time=estimated_time,
            file_count=len(valid_files),
            priority=priority
        )

    except Exception as e:
        # 清理已保存的临时文件
        if 'file_ids' in locals():
            for file_id in file_ids:
                await memory_file_handler.cleanup_file(file_id)

        logger.error("创建批量分析任务失败", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"创建批量任务失败: {str(e)}"
        )

async def _process_batch_analysis_task(task_id: str):
    """
    处理批量分析任务（后台运行）

    Args:
        task_id: 任务ID
    """
    if task_id not in batch_tasks:
        return

    task = batch_tasks[task_id]
    temp_file_paths = task["temp_file_paths"]
    request_params = task["request"]
    progress = task["progress"]
    timing = task["timing"]

    try:
        # 更新任务状态为处理中
        task["status"] = "processing"
        timing["started_at"] = datetime.now().isoformat()
        timing["updated_at"] = timing["started_at"]

        valid_files = task["valid_files"]
        total_files = len(valid_files)

        logger.info(
            "开始处理批量分析任务",
            task_id=task_id,
            total_files=total_files,
            priority=task["priority"]
        )

        for i, file_info in enumerate(valid_files):
            try:
                # 更新进度
                progress["current_file"] = file_info["filename"]
                progress["completed_count"] = len(progress["completed_files"])
                progress["failed_count"] = len(progress["failed_files"])
                overall_progress = (i / total_files) * 100
                task["progress"] = {**progress, "overall_progress": overall_progress}
                timing["updated_at"] = datetime.now().isoformat()

                logger.info(
                    "处理批量任务文件",
                    task_id=task_id,
                    file_index=i + 1,
                    total_files=total_files,
                    filename=file_info["filename"],
                    progress=f"{overall_progress:.1f}%"
                )

                # 创建单个文件分析请求（强制使用CPU）
                from ..models import AnalysisRequest, DeviceType
                single_request = AnalysisRequest(
                    model=request_params["model"],
                    device=DeviceType.CPU,  # 强制使用CPU
                    visualize=request_params["visualize"],
                    sonify=request_params["sonify"],
                    include_activations=request_params["include_activations"],
                    include_embeddings=request_params["include_embeddings"],
                    overwrite=request_params["overwrite"]
                )

                # 分析文件
                result_data, file_links = await analysis_service.analyze_single_file(
                    Path(file_info["temp_path"]),
                    single_request,
                    f"{task_id}_{i}"
                )

                # 保存结果
                progress["results"][file_info["filename"]] = {
                    "data": result_data,
                    "files": file_links,
                    "success": True
                }
                progress["completed_files"].append(file_info["filename"])

            except Exception as e:
                logger.error(
                    "批量任务文件处理失败",
                    task_id=task_id,
                    filename=file_info["filename"],
                    error=str(e)
                )

                progress["results"][file_info["filename"]] = {
                    "success": False,
                    "error": str(e)
                }
                progress["failed_files"].append(file_info["filename"])

                # 如果设置了不继续处理错误，则中断
                if not request_params["continue_on_error"]:
                    logger.warning(
                        "批量任务因错误中断",
                        task_id=task_id,
                        error=str(e)
                    )
                    break

        # 任务完成
        task["status"] = "completed"
        timing["completed_at"] = datetime.now().isoformat()
        timing["updated_at"] = timing["completed_at"]
        progress["current_file"] = None
        progress["overall_progress"] = 100.0
        task["progress"] = progress

        logger.info(
            "批量分析任务完成",
            task_id=task_id,
            completed_count=len(progress["completed_files"]),
            failed_count=len(progress["failed_files"]),
            total_processing_time=(
                datetime.fromisoformat(timing["completed_at"]) -
                datetime.fromisoformat(timing["started_at"])
            ).total_seconds()
        )

    except Exception as e:
        logger.error(
            "批量分析任务处理失败",
            task_id=task_id,
            error=str(e)
        )
        task["status"] = "failed"
        timing["updated_at"] = datetime.now().isoformat()

    finally:
        # 清理所有临时文件
        for file_id in task["file_ids"]:
            await memory_file_handler.cleanup_file(file_id)

@router.get(
    "/analyze/batch/{task_id}/status",
    summary="查询批量分析任务状态",
    description="""
    查询批量分析任务的执行状态和详细进度信息。

    ## 返回信息
    - 任务状态（pending/processing/completed/failed）
    - 详细进度（文件级别）
    - 已完成和失败的文件列表
    - 时间统计信息
    """
)
async def get_batch_analysis_status(task_id: str):
    """
    获取批量分析任务状态

    Args:
        task_id: 任务ID

    Returns:
        Dict: 任务状态和进度信息
    """
    if task_id not in batch_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"批量任务不存在: {task_id}"
        )

    task = batch_tasks[task_id]
    progress = task["progress"]
    timing = task["timing"]

    # 计算预计剩余时间
    estimated_remaining = None
    if task["status"] == "processing" and progress["completed_count"] > 0:
        elapsed_time = (
            datetime.now() -
            datetime.fromisoformat(timing["started_at"])
        ).total_seconds()

        avg_time_per_file = elapsed_time / progress["completed_count"]
        remaining_files = task["file_count"] - progress["completed_count"]
        estimated_seconds = remaining_files * avg_time_per_file

        if estimated_seconds > 0:
            estimated_remaining = f"{int(estimated_seconds // 60)}-{int((estimated_seconds // 60) + 1)}分钟"

    return {
        "task_id": task_id,
        "status": task["status"],
        "priority": task["priority"],
        "progress": {
            "overall_progress": progress.get("overall_progress", 0),
            "current_file": progress["current_file"],
            "completed_files": progress["completed_files"],
            "failed_files": progress["failed_files"],
            "file_count": task["file_count"],
            "completed_count": progress["completed_count"],
            "failed_count": progress["failed_count"],
            "estimated_remaining": estimated_remaining
        },
        "timing": {
            "created_at": timing["created_at"],
            "started_at": timing.get("started_at"),
            "updated_at": timing["updated_at"],
            "estimated_time": task["estimated_time"]
        },
        "file_summary": {
            "valid_files": len(task["valid_files"]),
            "invalid_files": len(task["invalid_files"]),
            "total_size_mb": task["total_size_mb"]
        }
    }

@router.get(
    "/analyze/batch/{task_id}/result",
    summary="获取批量分析结果",
    description="""
    获取已完成的批量分析任务的详细结果。

    ## 返回信息
    - 完整的分析结果列表
    - 每个文件的处理状态
    - 生成的文件下载链接
    - 错误信息（如果有）
    """
)
async def get_batch_analysis_result(task_id: str):
    """
    获取批量分析任务结果

    Args:
        task_id: 任务ID

    Returns:
        Dict: 批量分析结果
    """
    if task_id not in batch_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"批量任务不存在: {task_id}"
        )

    task = batch_tasks[task_id]
    progress = task["progress"]
    timing = task["timing"]

    response = {
        "task_id": task_id,
        "status": task["status"],
        "message": "批量分析完成" if task["status"] == "completed" else "分析失败",
        "file_count": task["file_count"],
        "completed_count": progress["completed_count"],
        "failed_count": progress["failed_count"],
        "timing": timing
    }

    if task["status"] == "completed":
        # 添加成功的结果
        results = []
        files = {}

        for filename, result_data in progress["results"].items():
            if result_data["success"]:
                results.append(result_data["data"])
                if result_data.get("files"):
                    files[filename] = result_data["files"]

        response["success"] = True
        response["results"] = results
        response["files"] = files
        response["total_processing_time"] = (
            datetime.fromisoformat(timing["completed_at"]) -
            datetime.fromisoformat(timing["started_at"])
        ).total_seconds() if timing.get("started_at") else None

    elif task["status"] == "failed":
        response["success"] = False
        response["error"] = "批量分析过程中出现错误"

    return response

@router.delete(
    "/analyze/batch/{task_id}",
    summary="取消或删除批量分析任务",
    description="""
    取消正在处理的批量任务或删除已完成的任务记录。

    ## 注意事项
    - 正在处理的任务只能取消，无法删除
    - 已完成的任务可以删除
    - 删除后无法恢复结果
    """
)
async def cancel_or_delete_batch_task(task_id: str):
    """
    取消或删除批量分析任务

    Args:
        task_id: 任务ID

    Returns:
        Dict: 操作结果
    """
    if task_id not in batch_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"批量任务不存在: {task_id}"
        )

    task = batch_tasks[task_id]

    if task["status"] in ["pending", "processing"]:
        # 取消正在处理的任务
        task["status"] = "cancelled"
        task["timing"]["updated_at"] = datetime.now().isoformat()

        logger.info("批量任务已取消", task_id=task_id)
        return {
            "success": True,
            "message": f"批量任务已取消: {task_id}"
        }
    elif task["status"] in ["completed", "failed", "cancelled"]:
        # 删除已完成的任务记录
        del batch_tasks[task_id]

        logger.info("批量任务记录已删除", task_id=task_id)
        return {
            "success": True,
            "message": f"批量任务记录已删除: {task_id}"
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"无法操作当前状态的任务: {task['status']}"
        )

@router.get(
    "/analyze/batch/list",
    summary="获取批量任务列表",
    description="""
    获取所有批量任务的简要信息列表。

    ## 返回信息
    - 任务ID列表
    - 任务状态和进度
    - 创建和更新时间
    - 文件数量统计
    """
)
async def list_batch_tasks(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    获取批量任务列表

    Args:
        status: 按状态过滤任务 (pending/processing/completed/failed/cancelled)
        limit: 返回结果数量限制

    Returns:
        Dict: 任务列表
    """
    try:
        tasks = []

        for task_id, task_data in batch_tasks.items():
            # 状态过滤
            if status and task_data["status"] != status:
                continue

            tasks.append({
                "task_id": task_id,
                "status": task_data["status"],
                "priority": task_data["priority"],
                "file_count": task_data["file_count"],
                "completed_count": len(task_data["progress"]["completed_files"]),
                "failed_count": len(task_data["progress"]["failed_files"]),
                "total_size_mb": task_data["total_size_mb"],
                "created_at": task_data["timing"]["created_at"],
                "updated_at": task_data["timing"]["updated_at"],
                "estimated_time": task_data.get("estimated_time")
            })

        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x["created_at"], reverse=True)

        # 限制结果数量
        tasks = tasks[:limit]

        return {
            "success": True,
            "total_count": len(tasks),
            "tasks": tasks
        }

    except Exception as e:
        logger.error("获取批量任务列表失败", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"获取任务列表失败: {str(e)}"
        )