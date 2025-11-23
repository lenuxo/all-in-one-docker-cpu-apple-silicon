"""
音频处理工具函数
"""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger()

async def get_audio_duration(file_path: Path) -> Optional[float]:
    """
    获取音频文件时长（秒）

    Args:
        file_path: 音频文件路径

    Returns:
        Optional[float]: 时长（秒），失败返回None
    """
    try:
        # 使用ffprobe获取音频信息
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            duration_str = result.stdout.strip()
            if duration_str:
                return float(duration_str)

        logger.warning("无法获取音频时长", file_path=str(file_path))
        return None

    except subprocess.TimeoutExpired:
        logger.error("获取音频时长超时", file_path=str(file_path))
        return None
    except Exception as e:
        logger.error("获取音频时长失败", error=str(e), file_path=str(file_path))
        return None

async def convert_to_wav(input_path: Path, output_path: Path) -> bool:
    """
    将音频文件转换为WAV格式

    Args:
        input_path: 输入文件路径
        output_path: 输出WAV文件路径

    Returns:
        bool: 转换是否成功
    """
    try:
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            '-ac', '2',
            '-y',  # 覆盖输出文件
            str(output_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        if result.returncode == 0 and output_path.exists():
            logger.info("音频格式转换成功",
                       input=str(input_path),
                       output=str(output_path))
            return True
        else:
            logger.error("音频格式转换失败",
                        input=str(input_path),
                        output=str(output_path),
                        stderr=result.stderr)
            return False

    except subprocess.TimeoutExpired:
        logger.error("音频格式转换超时", input=str(input_path))
        return False
    except Exception as e:
        logger.error("音频格式转换异常", error=str(e), input=str(input_path))
        return False

async def check_audio_format(file_path: Path) -> Tuple[str, bool]:
    """
    检查音频文件格式和有效性

    Args:
        file_path: 音频文件路径

    Returns:
        Tuple[str, bool]: (格式描述, 是否有效)
    """
    try:
        # 使用ffprobe检查文件
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'stream=codec_name,sample_rate,channels,duration',
            '-show_entries', 'format=format_name,duration',
            '-of', 'default=noprint_wrappers=1',
            str(file_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return "无法读取的音频文件", False

        # 解析输出信息
        output_lines = result.stdout.strip().split('\n')
        codec_info = {}

        for line in output_lines:
            if '=' in line:
                key, value = line.split('=', 1)
                codec_info[key.strip()] = value.strip()

        # 检查关键信息
        codec_name = codec_info.get('codec_name', 'unknown')
        sample_rate = codec_info.get('sample_rate', '0')
        channels = codec_info.get('channels', '0')
        duration = codec_info.get('duration', '0')

        if codec_name == 'unknown':
            return "未知的音频编码", False

        if sample_rate == '0':
            return "无效的采样率", False

        if channels == '0':
            return "无效的声道数", False

        # 格式化描述
        format_desc = f"音频格式: {codec_name}, 采样率: {sample_rate}Hz, 声道: {channels}"
        if duration != '0':
            format_desc += f", 时长: {float(duration):.1f}秒"

        return format_desc, True

    except subprocess.TimeoutExpired:
        return "音频文件检查超时", False
    except Exception as e:
        logger.error("音频格式检查失败", error=str(e), file_path=str(file_path))
        return f"音频格式检查失败: {str(e)}", False

def get_audio_file_info(file_path: Path) -> dict:
    """
    获取音频文件的详细信息

    Args:
        file_path: 音频文件路径

    Returns:
        dict: 音频文件信息
    """
    info = {
        "path": str(file_path),
        "size_bytes": file_path.stat().st_size,
        "exists": file_path.exists(),
        "duration": None,
        "format": "unknown",
        "sample_rate": None,
        "channels": None,
        "bitrate": None,
        "valid": False
    }

    if not file_path.exists():
        return info

    try:
        # 使用ffprobe获取详细信息
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'stream=codec_name,sample_rate,channels,duration,bit_rate',
            '-show_entries', 'format=format_name,size,duration,bit_rate',
            '-of', 'json',
            str(file_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)

            # 提取音频流信息
            streams = data.get('streams', [])
            audio_stream = None

            for stream in streams:
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break

            if audio_stream:
                info.update({
                    "format": audio_stream.get('codec_name', 'unknown'),
                    "sample_rate": int(audio_stream.get('sample_rate', 0)),
                    "channels": int(audio_stream.get('channels', 0)),
                    "duration": float(audio_stream.get('duration', 0)),
                    "valid": True
                })

                # 从format中获取比特率
                format_info = data.get('format', {})
                if format_info.get('bit_rate'):
                    info["bitrate"] = int(format_info.get('bit_rate', 0))

    except Exception as e:
        logger.error("获取音频文件信息失败", error=str(e), file_path=str(file_path))

    return info