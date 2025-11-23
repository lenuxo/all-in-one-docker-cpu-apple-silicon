"""
请求参数模型
定义API请求的数据结构
"""

from pydantic import BaseModel, Field
from typing import Optional
from .data_models import ModelType, DeviceType


class AnalysisRequest(BaseModel):
    """音频分析请求参数"""

    model: ModelType = Field(
        default=ModelType.HARMONIX_ALL,
        description="选择分析模型",
        example=ModelType.HARMONIX_ALL
    )

    device: DeviceType = Field(
        default=DeviceType.CPU,
        description="计算设备类型（默认CPU，当前仅支持CPU）",
        example=DeviceType.CPU
    )

    
    include_activations: bool = Field(
        default=False,
        description="是否包含原始激活数据（用于高级分析）",
        example=False
    )

    include_embeddings: bool = Field(
        default=False,
        description="是否包含嵌入向量数据",
        example=False
    )

    visualize: bool = Field(
        default=False,
        description="是否生成可视化图表",
        example=True
    )

    sonify: bool = Field(
        default=False,
        description="是否生成音频化文件",
        example=False
    )

    overwrite: bool = Field(
        default=False,
        description="是否覆盖已存在的分析结果",
        example=False
    )

    keep_byproducts: bool = Field(
        default=False,
        description="是否保留中间处理文件（音频分离、频谱图等）",
        example=False
    )

    class Config:
        schema_extra = {
            "example": {
                "model": "harmonix-all",
                                "include_activations": False,
                "include_embeddings": False,
                "visualize": True,
                "sonify": False,
                "overwrite": False,
                "keep_byproducts": False
            }
        }


class BatchAnalysisRequest(BaseModel):
    """批量分析请求参数"""

    model: ModelType = Field(
        default=ModelType.HARMONIX_ALL,
        description="选择分析模型",
        example=ModelType.HARMONIX_ALL
    )

    device: DeviceType = Field(
        default=DeviceType.CPU,
        description="计算设备类型（默认CPU，当前仅支持CPU）",
        example=DeviceType.CPU
    )

    
    include_activations: bool = Field(
        default=False,
        description="是否包含原始激活数据",
        example=False
    )

    include_embeddings: bool = Field(
        default=False,
        description="是否包含嵌入向量数据",
        example=False
    )

    visualize: bool = Field(
        default=True,
        description="是否生成可视化图表",
        example=True
    )

    sonify: bool = Field(
        default=False,
        description="是否生成音频化文件",
        example=False
    )

    overwrite: bool = Field(
        default=False,
        description="是否覆盖已存在的分析结果",
        example=False
    )

    email_notification: Optional[str] = Field(
        default=None,
        description="完成后发送通知邮件（可选）",
        example="user@example.com"
    )

    priority: int = Field(
        default=1,
        description="任务优先级（1-5，数字越大优先级越高）",
        ge=1,
        le=5,
        example=1
    )

    class Config:
        schema_extra = {
            "example": {
                "model": "harmonix-all",
                                "include_activations": False,
                "include_embeddings": False,
                "visualize": True,
                "sonify": False,
                "overwrite": False,
                "email_notification": None,
                "priority": 1
            }
        }