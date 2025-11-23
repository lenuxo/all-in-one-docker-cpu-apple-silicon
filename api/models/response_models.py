"""
响应模型
定义API响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from .data_models import Segment, BeatInfo


class AnalysisResult(BaseModel):
    """分析结果"""
    path: str = Field(description="音频文件路径", example="/tmp/uploads/song.wav")
    bpm: float = Field(description="每分钟节拍数", example=120.0, gt=0)
    beats: List[float] = Field(description="节拍时间点列表（秒）", example=[0.33, 0.75, 1.14, 1.56])
    downbeats: List[float] = Field(description="强拍时间点列表（秒）", example=[0.33, 1.94, 3.53])
    beat_positions: List[int] = Field(description="节拍位置列表（1=第一拍，2=第二拍等）", example=[1, 2, 3, 4, 1, 2, 3, 4])
    segments: List[Segment] = Field(description="音频段落列表")
    activations: Optional[Dict[str, Any]] = Field(
        default=None,
        description="原始激活数据（如果请求包含）",
        example={
            "beat": [0.1, 0.8, 0.9, 0.7],
            "downbeat": [0.9, 0.2, 0.1, 0.8],
            "segment": [0.1, 0.3, 0.9, 0.2],
            "label": [[0.1, 0.8, 0.1, 0.2], [0.3, 0.7, 0.9, 0.1]]
        }
    )
    embeddings: Optional[List[float]] = Field(
        default=None,
        description="嵌入向量数据（如果请求包含）",
        example=[0.1, 0.2, 0.3, 0.4, 0.5]
    )

    @property
    def duration(self) -> Optional[float]:
        """估算音频时长（基于最后一个段落的结束时间）"""
        if not self.segments:
            return None
        return max(segment.end for segment in self.segments)

    @property
    def segment_count(self) -> int:
        """段落数量"""
        return len(self.segments)

    @property
    def beat_count(self) -> int:
        """节拍数量"""
        return len(self.beats)


class FileLinks(BaseModel):
    """生成的文件下载链接"""
    visualization: Optional[str] = Field(
        default=None,
        description="可视化图表下载链接",
        example="/api/download/viz_song.pdf"
    )
    sonification: Optional[str] = Field(
        default=None,
        description="音频化文件下载链接",
        example="/api/download/sonif_song.wav"
    )
    json_result: Optional[str] = Field(
        default=None,
        description="JSON结果文件下载链接",
        example="/api/download/result_song.json"
    )
    activations: Optional[str] = Field(
        default=None,
        description="激活数据文件下载链接",
        example="/api/download/activations_song.npz"
    )
    embeddings: Optional[str] = Field(
        default=None,
        description="嵌入向量文件下载链接",
        example="/api/download/embeddings_song.npy"
    )


class AnalysisResponse(BaseModel):
    """分析API响应"""
    success: bool = Field(description="请求是否成功", example=True)
    message: str = Field(description="响应消息", example="分析完成")
    data: AnalysisResult = Field(description="分析结果数据")
    files: Optional[FileLinks] = Field(
        default=None,
        description="生成的文件下载链接"
    )
    processing_time: float = Field(
        description="处理耗时（秒）",
        example=15.23,
        ge=0
    )
    model_used: str = Field(description="使用的分析模型", example="harmonix-all")
    request_id: str = Field(description="请求唯一标识", example="req_20241123_001")


class BatchAnalysisResponse(BaseModel):
    """批量分析响应"""
    success: bool = Field(description="批量任务创建成功", example=True)
    task_id: str = Field(
        description="任务ID，用于查询结果",
        example="batch_analysis_20241123_001"
    )
    message: str = Field(description="响应消息", example="批量分析任务已创建，共3个文件")
    estimated_time: Optional[str] = Field(
        default=None,
        description="预计完成时间",
        example="45-60秒"
    )
    file_count: int = Field(description="文件数量", example=3)
    priority: int = Field(description="任务优先级", example=1)


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str = Field(description="任务ID", example="batch_analysis_20241123_001")
    status: Literal["pending", "processing", "completed", "failed", "cancelled"] = Field(
        description="任务状态",
        example="processing"
    )
    progress: float = Field(
        description="完成进度（0-100）",
        example=45.5,
        ge=0,
        le=100
    )
    current_file: Optional[str] = Field(
        default=None,
        description="当前处理的文件",
        example="song2.wav"
    )
    completed_files: List[str] = Field(
        default=[],
        description="已完成的文件列表",
        example=["song1.wav", "song3.wav"]
    )
    failed_files: List[str] = Field(
        default=[],
        description="失败的文件列表",
        example=[]
    )
    estimated_remaining: Optional[str] = Field(
        default=None,
        description="预计剩余时间",
        example="20-30秒"
    )
    created_at: str = Field(description="任务创建时间", example="2024-11-23T10:30:00Z")
    updated_at: str = Field(description="任务更新时间", example="2024-11-23T10:31:15Z")


class BatchResultResponse(BaseModel):
    """批量分析结果响应"""
    success: bool = Field(description="任务完成状态", example=True)
    task_id: str = Field(description="任务ID", example="batch_analysis_20241123_001")
    status: TaskStatus = Field(description="任务状态详情")
    results: Optional[List[AnalysisResult]] = Field(
        default=None,
        description="分析结果列表"
    )
    files: Optional[Dict[str, FileLinks]] = Field(
        default=None,
        description="每个文件对应的下载链接",
        example={
            "song1.wav": {"visualization": "/api/download/viz_song1.pdf"},
            "song2.wav": {"visualization": "/api/download/viz_song2.pdf"}
        }
    )
    total_processing_time: Optional[float] = Field(
        default=None,
        description="总处理时间（秒）",
        example=125.5
    )


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态", example="healthy")
    version: str = Field(description="API版本", example="1.0.0")
    uptime: str = Field(description="服务运行时间", example="2h 30m 15s")
    cpu_usage: float = Field(description="CPU使用率（%）", example=45.2)
    memory_usage: float = Field(description="内存使用率（%）", example=68.7)
    active_tasks: int = Field(description="当前活跃任务数", example=2)
    total_processed: int = Field(description="总处理文件数", example=156)
    models_loaded: List[str] = Field(
        description="已加载的模型",
        example=["harmonix-all", "harmonix-fold0"]
    )


class ErrorResponse(BaseModel):
    """错误响应格式"""
    success: bool = Field(default=False, description="请求失败")
    message: str = Field(description="错误描述")
    error_code: str = Field(description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    request_id: Optional[str] = Field(None, description="请求ID")


class AsyncAnalysisSubmitResponse(BaseModel):
    """异步分析任务提交响应"""
    success: bool = Field(description="任务提交是否成功", example=True)
    message: str = Field(description="响应消息", example="分析任务已创建")
    task_id: str = Field(description="任务ID，用于查询结果", example="task_20241123_001")
    request_id: str = Field(description="请求ID，用于进度跟踪", example="req_20241123_001")
    estimated_time: Optional[str] = Field(
        default=None,
        description="预估处理时间",
        example="45-90秒"
    )
    status_url: str = Field(
        description="任务状态查询URL",
        example="/api/analyze/task/task_20241123_001/status"
    )


class AsyncTaskStatus(BaseModel):
    """异步任务状态"""
    task_id: str = Field(description="任务ID", example="task_20241123_001")
    request_id: str = Field(description="请求ID", example="req_20241123_001")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        description="任务状态",
        example="processing"
    )
    progress: float = Field(
        description="任务进度（0-100）",
        example=65.5,
        ge=0,
        le=100
    )
    current_step: str = Field(
        description="当前处理步骤",
        example="audio_separation"
    )
    message: str = Field(
        description="状态消息",
        example="正在分析音频文件"
    )
    created_at: str = Field(description="创建时间", example="2024-11-23T10:30:00Z")
    updated_at: str = Field(description="更新时间", example="2024-11-23T10:31:15Z")
    estimated_remaining: Optional[str] = Field(
        default=None,
        description="预计剩余时间",
        example="20-30秒"
    )
    error: Optional[str] = Field(default=None, description="错误信息")


class AsyncAnalysisResult(BaseModel):
    """异步分析结果响应 - 与同步分析格式完全一致"""
    success: bool = Field(description="请求是否成功", example=True)
    message: str = Field(description="响应消息", example="分析完成")
    data: AnalysisResult = Field(description="分析结果数据")
    files: Optional[FileLinks] = Field(
        default=None,
        description="生成的文件下载链接"
    )
    processing_time: float = Field(
        description="处理耗时（秒）",
        example=30.5,
        ge=0
    )
    model_used: str = Field(description="使用的分析模型", example="harmonix-all")
    request_id: str = Field(description="请求唯一标识", example="req_20241123_001")
    task_id: str = Field(description="任务ID", example="task_20241123_001")


class BatchFileInfo(BaseModel):
    """批量任务文件信息"""
    filename: str = Field(description="文件名", example="song1.wav")
    size_bytes: Optional[int] = Field(default=None, description="文件大小（字节）")
    size_mb: Optional[float] = Field(default=None, description="文件大小（MB）", example=15.2)
    status: str = Field(description="文件验证状态", example="valid")
    error: Optional[str] = Field(default=None, description="错误信息")
    temp_path: Optional[str] = Field(default=None, description="临时文件路径")
    file_id: Optional[str] = Field(default=None, description="文件ID")
    duration: Optional[float] = Field(default=None, description="音频时长（秒）")


class BatchProgress(BaseModel):
    """批量任务进度信息"""
    overall_progress: Optional[float] = Field(default=None, description="总体进度（0-100）")
    current_file: Optional[str] = Field(default=None, description="当前处理的文件")
    completed_files: List[str] = Field(default=[], description="已完成的文件列表")
    failed_files: List[str] = Field(default=[], description="失败的文件列表")
    file_count: Optional[int] = Field(default=None, description="总文件数")
    completed_count: Optional[int] = Field(default=None, description="已完成文件数")
    failed_count: Optional[int] = Field(default=None, description="失败文件数")
    estimated_remaining: Optional[str] = Field(default=None, description="预计剩余时间")


class BatchTiming(BaseModel):
    """批量任务时间信息"""
    created_at: str = Field(description="任务创建时间", example="2024-11-23T10:30:00Z")
    started_at: Optional[str] = Field(default=None, description="任务开始时间")
    updated_at: str = Field(description="任务更新时间", example="2024-11-23T10:31:15Z")
    completed_at: Optional[str] = Field(default=None, description="任务完成时间")
    estimated_time: Optional[str] = Field(default=None, description="预估处理时间")


class BatchTaskSummary(BaseModel):
    """批量任务摘要"""
    task_id: str = Field(description="任务ID")
    status: str = Field(description="任务状态")
    priority: int = Field(description="任务优先级")
    file_count: int = Field(description="文件数量")
    completed_count: int = Field(description="已完成数量")
    failed_count: int = Field(description="失败数量")
    total_size_mb: float = Field(description="总文件大小（MB）")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    estimated_time: Optional[str] = Field(default=None, description="预估时间")


class BatchStatusResponse(BaseModel):
    """批量任务状态响应"""
    task_id: str = Field(description="任务ID")
    status: str = Field(description="任务状态")
    priority: int = Field(description="任务优先级")
    progress: BatchProgress = Field(description="进度信息")
    timing: BatchTiming = Field(description="时间信息")
    file_summary: Dict[str, Any] = Field(description="文件统计摘要")


class BatchListResponse(BaseModel):
    """批量任务列表响应"""
    success: bool = Field(description="查询是否成功", example=True)
    total_count: int = Field(description="任务总数", example=5)
    tasks: List[BatchTaskSummary] = Field(description="任务列表")


class ProgressStatus(BaseModel):
    """进度状态信息"""
    request_id: str = Field(description="请求ID")
    current_step: str = Field(description="当前分析步骤")
    step_description: str = Field(description="步骤描述")
    step_progress: float = Field(description="步骤进度（0-100）", example=65.0)
    overall_progress: float = Field(description="总体进度（0-100）", example=72.3)
    elapsed_time: float = Field(description="已用时间（秒）", example=35.2)
    estimated_remaining: Optional[str] = Field(default=None, description="预计剩余时间", example="1分20秒")
    step_start_time: float = Field(description="步骤开始时间戳")


class ProgressSummary(BaseModel):
    """进度摘要信息"""
    total_active: int = Field(description="活跃任务总数", example=3)
    by_step: Dict[str, int] = Field(description="各步骤任务数量", example={"audio_separation": 1, "beat_tracking": 2})
    average_progress: float = Field(description="平均进度", example=65.5)
    active_tasks: Optional[List[Dict[str, Any]]] = Field(default=None, description="活跃任务详情")


class AsyncAnalysisData(BaseModel):
    """异步分析数据"""
    bpm: float = Field(description="每分钟节拍数", example=120.5)
    beats: List[float] = Field(description="节拍时间点数组", example=[0.33, 0.75, 1.14, 1.56])
    downbeats: List[float] = Field(description="强拍时间点数组", example=[0.33, 1.94, 3.53])
    beat_positions: List[int] = Field(description="节拍位置数组", example=[1, 2, 3, 4, 1, 2, 3, 4])
    segments: List[Dict[str, Any]] = Field(
        description="音乐段落数组",
        example=[
            {"start": 0.0, "end": 0.33, "label": "start"},
            {"start": 0.33, "end": 13.13, "label": "intro"},
            {"start": 13.13, "end": 37.53, "label": "chorus"}
        ]
    )


class AsyncAnalysisFile(BaseModel):
    """异步分析生成文件"""
    url: str = Field(description="下载链接", example="/api/files/download/result_20241123_001.json")
    filename: str = Field(description="文件名", example="result_20241123_001.json")
    size: str = Field(description="文件大小", example="2.3KB")


class AsyncAnalysisFiles(BaseModel):
    """异步分析生成文件集合"""
    result_json: AsyncAnalysisFile = Field(description="分析结果JSON文件")


class AsyncAnalysisResultSuccess(BaseModel):
    """异步分析成功结果"""
    success: bool = Field(default=True, description="请求是否成功", example=True)
    message: str = Field(description="状态消息", example="分析完成")
    data: AsyncAnalysisData = Field(description="分析结果数据")
    files: AsyncAnalysisFiles = Field(description="生成文件信息")
    processing_time: float = Field(description="处理时间（秒）", example=30.5)


class AsyncAnalysisResultPending(BaseModel):
    """异步分析排队中结果"""
    success: bool = Field(default=False, description="请求是否成功", example=False)
    message: str = Field(description="状态消息", example="任务排队中，请稍后再试")


class AsyncAnalysisResultProcessing(BaseModel):
    """异步分析进行中结果"""
    success: bool = Field(default=False, description="请求是否成功", example=False)
    message: str = Field(description="状态消息", example="正在分析中，请稍后再试")
    progress_url: str = Field(description="进度查询URL", example="/api/progress/req_20241123_001")


class AsyncAnalysisResultFailed(BaseModel):
    """异步分析失败结果"""
    success: bool = Field(default=False, description="请求是否成功", example=False)
    message: str = Field(description="状态消息", example="分析失败")
    error: str = Field(description="错误信息", example="音频格式不支持")


class SystemInfo(BaseModel):
    """分析服务信息"""
    service: str = Field(description="服务名称", example="音乐分析API")
    version: str = Field(description="服务版本", example="1.0.0")
    models: Dict[str, Dict[str, Any]] = Field(description="可用模型信息")
    limitations: Dict[str, str] = Field(description="使用限制")
    supported_formats: Dict[str, Dict[str, Any]] = Field(description="支持的文件格式")
    features: Dict[str, bool] = Field(description="功能特性")