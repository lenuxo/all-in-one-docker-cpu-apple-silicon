"""
文件管理API端点
处理文件上传、下载和管理相关的请求
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
import structlog

from ..models import ErrorResponse

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()

# 文件存储路径
RESULTS_DIR = Path("api/static/results")

@router.get(
    "/download/{task_id}/{filename}",
    summary="下载分析结果文件",
    description="""
    下载音频分析生成的文件，包括：
    - 可视化图表（PDF）
    - 音频化文件（WAV）
    - JSON结果文件
    - 原始数据文件（NPZ/NPY）

    ## 使用方式
    从分析结果的 `files` 字段中获取下载链接，或直接使用此端点。

    ## 文件访问权限
    - 文件只能通过指定的任务ID和文件名访问
    - 路径验证确保无法访问系统中的其他文件
    - 24小时后文件可能被自动清理
    """
)
async def download_file(task_id: str, filename: str):
    """
    下载分析结果文件
    """
    try:
        # 验证文件路径，防止目录遍历攻击
        safe_task_id = os.path.basename(task_id)
        safe_filename = os.path.basename(filename)

        if not safe_task_id or not safe_filename:
            raise HTTPException(status_code=400, detail="无效的参数")

        # 构建文件路径
        file_path = RESULTS_DIR / f"analysis_{safe_task_id}" / safe_filename

        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"文件不存在: {filename}"
            )

        # 检查文件是否在正确的目录中（防止路径遍历）
        try:
            file_path.resolve().relative_to(RESULTS_DIR.resolve())
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="访问被拒绝"
            )

        # 确定MIME类型
        mime_type = _get_mime_type(filename)

        logger.info(
            "文件下载",
            task_id=task_id,
            filename=filename,
            file_size=file_path.stat().st_size
        )

        return FileResponse(
            path=str(file_path),
            filename=safe_filename,
            media_type=mime_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "文件下载失败",
            task_id=task_id,
            filename=filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"文件下载失败: {str(e)}"
        )

@router.delete(
    "/cleanup/{task_id}",
    summary="清理任务文件",
    description="""
    删除指定任务的所有相关文件，包括：
    - 原始上传文件
    - 分析结果文件
    - 临时文件

    ## 使用场景
    - 节省存储空间
    - 清理敏感数据
    - 任务完成后自动清理
    """
)
async def cleanup_task_files(task_id: str):
    """
    清理任务相关文件
    """
    try:
        safe_task_id = os.path.basename(task_id)
        if not safe_task_id:
            raise HTTPException(status_code=400, detail="无效的任务ID")

        # 删除结果目录
        results_path = RESULTS_DIR / f"analysis_{safe_task_id}"
        deleted_files = []

        if results_path.exists():
            for file_path in results_path.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    deleted_files.append(file_path.name)
            results_path.rmdir()

        logger.info(
            "任务文件清理完成",
            task_id=task_id,
            deleted_files_count=len(deleted_files),
            deleted_files=deleted_files
        )

        return {
            "success": True,
            "message": f"任务 {task_id} 的文件已清理",
            "deleted_files": deleted_files,
            "deleted_count": len(deleted_files)
        }

    except Exception as e:
        logger.error(
            "任务文件清理失败",
            task_id=task_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"文件清理失败: {str(e)}"
        )

def _get_mime_type(filename: str) -> str:
    """
    根据文件扩展名确定MIME类型

    Args:
        filename: 文件名

    Returns:
        str: MIME类型
    """
    extension_map = {
        ".pdf": "application/pdf",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".json": "application/json",
        ".npz": "application/octet-stream",
        ".npy": "application/octet-stream",
        ".zip": "application/zip"
    }

    # 获取文件扩展名
    if "." in filename:
        ext = filename.lower().split(".")[-1]
        ext_with_dot = f".{ext}"
        return extension_map.get(ext_with_dot, "application/octet-stream")

    return "application/octet-stream"