"""
文件处理工具函数
"""

import os
import uuid
import aiofiles
import time
from pathlib import Path
from typing import Tuple, Optional
import structlog

logger = structlog.get_logger()

# 移除了API层的文件大小和音频时长限制，让核心库决定处理能力

# 支持的音频格式
SUPPORTED_FORMATS = {
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/mp3": "mp3",
    "audio/mpeg": "mp3",
    "audio/mpeg3": "mp3",
    "audio/x-mpeg-3": "mp3"
}

async def validate_audio_file(file) -> Tuple[bool, Optional[str]]:
    """
    验证上传的音频文件

    Args:
        file: UploadFile对象

    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误信息)
    """
    try:
        # 检查文件格式
        content_type = file.content_type or ""
        if content_type not in SUPPORTED_FORMATS:
            return False, f"不支持的文件格式: {content_type}。支持的格式: {', '.join(SUPPORTED_FORMATS.keys())}"

        # 检查文件是否为空
        content = await file.read(1)  # 只读取1字节来检查是否为空
        if not content:
            return False, "文件为空"

        # 重置文件指针
        await file.seek(0)

        return True, None

    except Exception as e:
        logger.error("文件验证失败", error=str(e), filename=file.filename)
        return False, f"文件验证失败: {str(e)}"

async def get_file_info(file) -> dict:
    """
    获取文件信息

    Args:
        file: UploadFile对象

    Returns:
        dict: 文件信息
    """
    try:
        # 读取文件内容以获取大小
        content = await file.read()
        file_size = len(content)
        # 重置文件指针
        await file.seek(0)

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "extension": SUPPORTED_FORMATS.get(file.content_type, "unknown")
        }
    except Exception as e:
        logger.error("获取文件信息失败", error=str(e), filename=file.filename)
        return {
            "filename": file.filename,
            "error": str(e)
        }

def generate_unique_filename(original_name: str) -> str:
    """
    生成唯一的文件名

    Args:
        original_name: 原始文件名

    Returns:
        str: 唯一文件名
    """
    # 获取文件扩展名
    if "." in original_name:
        stem = original_name.rsplit(".", 1)[0]
        ext = original_name.rsplit(".", 1)[1]
    else:
        stem = original_name
        ext = ""

    # 生成唯一ID
    unique_id = str(uuid.uuid4())[:8]
    timestamp = int(time.time())

    # 组合文件名
    if ext:
        return f"{stem}_{timestamp}_{unique_id}.{ext}"
    else:
        return f"{stem}_{timestamp}_{unique_id}"

async def save_upload_file(upload_file, destination: Path) -> bool:
    """
    保存上传的文件

    Args:
        upload_file: UploadFile对象
        destination: 目标路径

    Returns:
        bool: 是否成功
    """
    try:
        async with aiofiles.open(destination, 'wb') as f:
            content = await upload_file.read()
            await f.write(content)
        return True
    except Exception as e:
        logger.error("保存文件失败", error=str(e), destination=str(destination))
        return False

def cleanup_temp_files(temp_dir: Path, max_age_hours: int = 24):
    """
    清理临时文件

    Args:
        temp_dir: 临时目录路径
        max_age_hours: 文件最大保存时间（小时）
    """
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        if not temp_dir.exists():
            return

        cleaned_count = 0
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    cleaned_count += 1

        logger.info("临时文件清理完成", cleaned_count=cleaned_count, temp_dir=str(temp_dir))

    except Exception as e:
        logger.error("清理临时文件失败", error=str(e), temp_dir=str(temp_dir))

async def ensure_directory(path: Path) -> bool:
    """
    确保目录存在

    Args:
        path: 目录路径

    Returns:
        bool: 是否成功
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error("创建目录失败", error=str(e), path=str(path))
        return False