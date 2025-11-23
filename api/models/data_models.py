"""
数据模型定义
定义音频分析相关的数据结构和枚举类型
"""

from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class ModelType(str, Enum):
    """可用的分析模型"""
    HARMONIX_ALL = "harmonix-all"
    HARMONIX_FOLD0 = "harmonix-fold0"
    HARMONIX_FOLD1 = "harmonix-fold1"
    HARMONIX_FOLD2 = "harmonix-fold2"
    HARMONIX_FOLD3 = "harmonix-fold3"
    HARMONIX_FOLD4 = "harmonix-fold4"
    HARMONIX_FOLD5 = "harmonix-fold5"
    HARMONIX_FOLD6 = "harmonix-fold6"
    HARMONIX_FOLD7 = "harmonix-fold7"

    def get_description(self) -> str:
        """获取模型描述"""
        descriptions = {
            "harmonix-all": "集成8个模型的平均结果（最高精度）",
            "harmonix-fold0": "第0折模型（单模型）",
            "harmonix-fold1": "第1折模型（单模型）",
            "harmonix-fold2": "第2折模型（单模型）",
            "harmonix-fold3": "第3折模型（单模型）",
            "harmonix-fold4": "第4折模型（单模型）",
            "harmonix-fold5": "第5折模型（单模型）",
            "harmonix-fold6": "第6折模型（单模型）",
            "harmonix-fold7": "第7折模型（单模型）",
        }
        return descriptions.get(self.value, "未知模型")


class DeviceType(str, Enum):
    """计算设备类型"""
    CPU = "cpu"
    CUDA = "cuda"


class SegmentLabel(str, Enum):
    """段落标签类型"""
    START = "start"
    END = "end"
    INTRO = "intro"
    OUTRO = "outro"
    VERSE = "verse"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    BREAK = "break"
    INST = "inst"
    SOLO = "solo"


class Segment(BaseModel):
    """音频段落信息"""
    start: float = Field(description="段落开始时间（秒）", example=13.13, ge=0.0)
    end: float = Field(description="段落结束时间（秒）", example=37.53, gt=0)
    label: SegmentLabel = Field(description="段落类型标签", example=SegmentLabel.CHORUS)

    @property
    def duration(self) -> float:
        """计算段落时长"""
        return self.end - self.start

    class Config:
        schema_extra = {
            "example": {
                "start": 13.13,
                "end": 37.53,
                "label": "chorus"
            }
        }


class BeatInfo(BaseModel):
    """节拍信息"""
    bpm: float = Field(description="每分钟节拍数", example=120.0, gt=0)
    beats: List[float] = Field(description="节拍时间点列表（秒）", example=[0.33, 0.75, 1.14, 1.56, 1.98])
    downbeats: List[float] = Field(description="强拍时间点列表（秒）", example=[0.33, 1.94, 3.53])
    beat_positions: List[int] = Field(description="节拍位置列表（1=第一拍，2=第二拍等）", example=[1, 2, 3, 4, 1, 2, 3, 4])

    @property
    def beat_count(self) -> int:
        """节拍总数"""
        return len(self.beats)

    @property
    def downbeat_count(self) -> int:
        """强拍总数"""
        return len(self.downbeats)

    class Config:
        schema_extra = {
            "example": {
                "bpm": 120.0,
                "beats": [0.33, 0.75, 1.14, 1.56, 1.98],
                "downbeats": [0.33, 1.94, 3.53],
                "beat_positions": [1, 2, 3, 4, 1, 2, 3, 4]
            }
        }