"""
API数据模型定义
包含请求参数、响应格式和错误处理模型
"""

from .request_models import AnalysisRequest, BatchAnalysisRequest
from .response_models import (
    AnalysisResult,
    AnalysisResponse,
    BatchAnalysisResponse,
    BatchResultResponse,
    ErrorResponse,
    HealthResponse,
    FileLinks,
    TaskStatus,
    # 异步分析响应模型
    AsyncAnalysisSubmitResponse,
    AsyncTaskStatus,
    AsyncAnalysisResult,
    BatchFileInfo,
    BatchProgress,
    BatchTiming,
    BatchTaskSummary,
    BatchStatusResponse,
    BatchListResponse,
    ProgressStatus,
    ProgressSummary,
    SystemInfo,
    # 异步分析结果相关模型
    AsyncAnalysisData,
    AsyncAnalysisFile,
    AsyncAnalysisFiles,
    AsyncAnalysisResultSuccess,
    AsyncAnalysisResultPending,
    AsyncAnalysisResultProcessing,
    AsyncAnalysisResultFailed
)
from .data_models import Segment, SegmentLabel, ModelType, DeviceType

__all__ = [
    # Request models
    "AnalysisRequest",
    "BatchAnalysisRequest",

    # Response models
    "AnalysisResult",
    "AnalysisResponse",
    "BatchAnalysisResponse",
    "BatchResultResponse",
    "ErrorResponse",
    "HealthResponse",
    "FileLinks",
    "TaskStatus",

    # 异步分析响应模型
    "AsyncAnalysisSubmitResponse",
    "AsyncTaskStatus",
    "AsyncAnalysisResult",
    "BatchFileInfo",
    "BatchProgress",
    "BatchTiming",
    "BatchTaskSummary",
    "BatchStatusResponse",
    "BatchListResponse",
    "ProgressStatus",
    "ProgressSummary",
    "SystemInfo",

    # 异步分析结果相关模型
    "AsyncAnalysisData",
    "AsyncAnalysisFile",
    "AsyncAnalysisFiles",
    "AsyncAnalysisResultSuccess",
    "AsyncAnalysisResultPending",
    "AsyncAnalysisResultProcessing",
    "AsyncAnalysisResultFailed",

    # Data models
    "Segment",
    "SegmentLabel",
    "ModelType",
    "DeviceType"
]