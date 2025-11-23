"""
内存文件处理工具
临时存储上传的文件到内存中，分析完成后自动清理
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Tuple, Optional, BinaryIO, AsyncGenerator
import structlog
import aiofiles
import aiofiles.os
from fastapi import HTTPException

logger = structlog.get_logger()

class MemoryFileHandler:
    """内存文件处理器"""

    def __init__(self):
        self.temp_files = {}  # 跟踪临时文件

    async def save_to_temp(self, upload_file) -> Tuple[Path, str]:
        """
        将上传文件保存到临时目录

        Args:
            upload_file: UploadFile对象

        Returns:
            Tuple[Path, str]: (临时文件路径, 文件ID)
        """
        try:
            # 生成唯一的文件ID和临时路径
            file_id = str(uuid.uuid4())
            temp_dir = Path(tempfile.gettempdir()) / "music_analysis" / file_id
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 使用原始文件名加上安全的时间戳
            original_name = upload_file.filename or "audio"
            if "." in original_name:
                stem = original_name.rsplit(".", 1)[0]
                ext = original_name.rsplit(".", 1)[1]
                safe_filename = f"{stem}_{file_id[:8]}.{ext}"
            else:
                safe_filename = f"{original_name}_{file_id[:8]}"

            temp_file_path = temp_dir / safe_filename

            # 保存文件到临时目录
            async with aiofiles.open(temp_file_path, 'wb') as f:
                content = await upload_file.read()
                await f.write(content)

            # 记录文件信息用于后续清理
            self.temp_files[file_id] = {
                "path": temp_file_path,
                "dir": temp_dir,
                "created_at": os.times()[4]  # 进程时间
            }

            logger.info(
                "文件保存到临时目录",
                file_id=file_id,
                original_name=original_name,
                temp_path=str(temp_file_path),
                size=len(content)
            )

            # 重置文件指针
            await upload_file.seek(0)

            return temp_file_path, file_id

        except Exception as e:
            logger.error("保存临时文件失败", error=str(e), filename=upload_file.filename)
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

    async def cleanup_file(self, file_id: str) -> bool:
        """
        清理指定文件ID的临时文件

        Args:
            file_id: 文件ID

        Returns:
            bool: 是否成功清理
        """
        try:
            if file_id not in self.temp_files:
                logger.warning("文件ID不存在，跳过清理", file_id=file_id)
                return False

            file_info = self.temp_files[file_id]
            temp_dir = file_info["dir"]
            temp_file_path = file_info["path"]

            # 删除临时文件
            if temp_file_path.exists():
                await aiofiles.os.remove(temp_file_path)
                logger.info("临时文件已删除", file_id=file_id, path=str(temp_file_path))

            # 删除临时目录
            if temp_dir.exists():
                await aiofiles.os.rmdir(temp_dir)
                logger.info("临时目录已删除", file_id=file_id, dir=str(temp_dir))

            # 从跟踪记录中移除
            del self.temp_files[file_id]

            return True

        except Exception as e:
            logger.error("清理临时文件失败", file_id=file_id, error=str(e))
            return False

    async def cleanup_all(self) -> int:
        """清理所有临时文件"""
        cleaned_count = 0
        file_ids = list(self.temp_files.keys())  # 复制键列表避免修改字典时迭代

        for file_id in file_ids:
            if await self.cleanup_file(file_id):
                cleaned_count += 1

        logger.info("批量清理完成", cleaned_count=cleaned_count, total=len(file_ids))
        return cleaned_count

    async def get_file_size(self, file_id: str) -> Optional[int]:
        """获取文件大小"""
        if file_id not in self.temp_files:
            return None

        try:
            file_path = self.temp_files[file_id]["path"]
            if file_path.exists():
                return file_path.stat().st_size
        except Exception as e:
            logger.error("获取文件大小失败", file_id=file_id, error=str(e))

        return None

    def get_file_count(self) -> int:
        """获取当前存储的文件数量"""
        return len(self.temp_files)

    def get_total_size(self) -> int:
        """获取所有临时文件的总大小"""
        total_size = 0
        for file_info in self.temp_files.values():
            try:
                if file_info["path"].exists():
                    total_size += file_info["path"].stat().st_size
            except Exception:
                continue

        return total_size

# 全局实例
memory_file_handler = MemoryFileHandler()

async def cleanup_expired_files(max_age_minutes: int = 30):
    """
    清理过期的临时文件

    Args:
        max_age_minutes: 最大保存时间（分钟）
    """
    import time

    current_time = os.times()[4]
    expired_files = []

    for file_id, file_info in memory_file_handler.temp_files.items():
        age_minutes = (current_time - file_info["created_at"]) / 60
        if age_minutes > max_age_minutes:
            expired_files.append(file_id)

    for file_id in expired_files:
        await memory_file_handler.cleanup_file(file_id)

    if expired_files:
        logger.info(
            "过期文件清理完成",
            cleaned_count=len(expired_files),
            max_age_minutes=max_age_minutes
        )

# 后台清理任务
async def schedule_cleanup():
    """定期清理任务"""
    try:
        await cleanup_expired_files(max_age_minutes=30)
        await memory_file_handler.cleanup_all()
    except Exception as e:
        logger.error("定期清理任务失败", error=str(e))