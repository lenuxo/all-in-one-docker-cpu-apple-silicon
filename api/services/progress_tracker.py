"""
分析进度跟踪器
提供单文件分析的详细进度跟踪功能
"""

import time
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger()

class AnalysisStep(str, Enum):
    """分析步骤枚举"""
    INITIALIZING = "initializing"
    LOADING_MODEL = "loading_model"
    AUDIO_SEPARATION = "audio_separation"
    SPECTROGRAM_EXTRACTION = "spectrogram_extraction"
    FEATURE_EXTRACTION = "feature_extraction"
    BEAT_TRACKING = "beat_tracking"
    SEGMENT_ANALYSIS = "segment_analysis"
    GENERATING_RESULTS = "generating_results"
    SAVING_OUTPUTS = "saving_outputs"
    COMPLETED = "completed"

class ProgressTracker:
    """单文件分析进度跟踪器"""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = time.time()
        self.current_step = AnalysisStep.INITIALIZING
        self.step_progress = 0.0  # 当前步骤的进度 (0-100)
        self.overall_progress = 0.0  # 总体进度 (0-100)
        self.step_start_time = time.time()
        self.step_estimates = {
            AnalysisStep.INITIALIZING: (1, 2),      # 1-2秒
            AnalysisStep.LOADING_MODEL: (5, 15),     # 5-15秒
            AnalysisStep.AUDIO_SEPARATION: (10, 30), # 10-30秒
            AnalysisStep.SPECTROGRAM_EXTRACTION: (5, 15),  # 5-15秒
            AnalysisStep.FEATURE_EXTRACTION: (3, 8), # 3-8秒
            AnalysisStep.BEAT_TRACKING: (5, 12),     # 5-12秒
            AnalysisStep.SEGMENT_ANALYSIS: (8, 20),  # 8-20秒
            AnalysisStep.GENERATING_RESULTS: (2, 5), # 2-5秒
            AnalysisStep.SAVING_OUTPUTS: (1, 3),     # 1-3秒
        }
        self.step_descriptions = {
            AnalysisStep.INITIALIZING: "初始化分析环境",
            AnalysisStep.LOADING_MODEL: "加载深度学习模型",
            AnalysisStep.AUDIO_SEPARATION: "音轨分离处理",
            AnalysisStep.SPECTROGRAM_EXTRACTION: "提取频谱图特征",
            AnalysisStep.FEATURE_EXTRACTION: "提取音频特征",
            AnalysisStep.BEAT_TRACKING: "节拍检测分析",
            AnalysisStep.SEGMENT_ANALYSIS: "音乐段落分析",
            AnalysisStep.GENERATING_RESULTS: "生成分析结果",
            AnalysisStep.SAVING_OUTPUTS: "保存输出文件",
            AnalysisStep.COMPLETED: "分析完成"
        }

        # 全局进度跟踪存储
        ProgressTracker._active_trackers[request_id] = self

    # 全局进度跟踪器存储
    _active_trackers: Dict[str, 'ProgressTracker'] = {}

    @classmethod
    def get_tracker(cls, request_id: str) -> Optional['ProgressTracker']:
        """获取进度跟踪器"""
        return cls._active_trackers.get(request_id)

    @classmethod
    def remove_tracker(cls, request_id: str) -> bool:
        """移除进度跟踪器"""
        if request_id in cls._active_trackers:
            del cls._active_trackers[request_id]
            return True
        return False

    @classmethod
    def cleanup_expired(cls, max_age_hours: int = 24):
        """清理过期的进度跟踪器"""
        current_time = time.time()
        expired_ids = []

        for request_id, tracker in cls._active_trackers.items():
            age_seconds = current_time - tracker.start_time
            age_hours = age_seconds / 3600
            if age_hours > max_age_hours:
                expired_ids.append(request_id)

        for request_id in expired_ids:
            cls.remove_tracker(request_id)

        logger.info(
            "进度跟踪器清理完成",
            cleaned_count=len(expired_ids),
            remaining_count=len(cls._active_trackers)
        )

        return len(expired_ids)

    def update_step(self, step: AnalysisStep, step_progress: float = 0.0):
        """
        更新分析步骤

        Args:
            step: 当前分析步骤
            step_progress: 当前步骤的进度 (0-100)
        """
        old_step = self.current_step
        self.current_step = step
        self.step_progress = max(0, min(100, step_progress))
        self.step_start_time = time.time()

        # 计算总体进度
        self.overall_progress = self._calculate_overall_progress()

        # 记录日志
        if old_step != step:
            logger.info(
                "分析步骤更新",
                request_id=self.request_id,
                old_step=old_step.value,
                new_step=step.value,
                step_description=self.step_descriptions.get(step, ""),
                overall_progress=self.overall_progress
            )

    def update_step_progress(self, progress: float):
        """更新当前步骤的进度"""
        self.step_progress = max(0, min(100, progress))
        self.overall_progress = self._calculate_overall_progress()

    def _calculate_overall_progress(self) -> float:
        """计算总体进度"""
        # 为每个步骤分配权重
        step_weights = {
            AnalysisStep.INITIALIZING: 0.02,
            AnalysisStep.LOADING_MODEL: 0.15,
            AnalysisStep.AUDIO_SEPARATION: 0.25,
            AnalysisStep.SPECTROGRAM_EXTRACTION: 0.15,
            AnalysisStep.FEATURE_EXTRACTION: 0.08,
            AnalysisStep.BEAT_TRACKING: 0.15,
            AnalysisStep.SEGMENT_ANALYSIS: 0.15,
            AnalysisStep.GENERATING_RESULTS: 0.03,
            AnalysisStep.SAVING_OUTPUTS: 0.02,
            AnalysisStep.COMPLETED: 1.0
        }

        # 计算已完成步骤的总权重
        completed_weight = 0.0
        for step, weight in step_weights.items():
            if step == self.current_step:
                completed_weight += weight * (self.step_progress / 100)
                break
            elif step.value < self.current_step.value:
                completed_weight += weight

        return round(completed_weight * 100, 1)

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        elapsed_time = time.time() - self.start_time

        # 估算剩余时间
        estimated_remaining = self._estimate_remaining_time()

        return {
            "request_id": self.request_id,
            "current_step": self.current_step.value,
            "step_description": self.step_descriptions.get(self.current_step, ""),
            "step_progress": round(self.step_progress, 1),
            "overall_progress": self.overall_progress,
            "elapsed_time": round(elapsed_time, 1),
            "estimated_remaining": estimated_remaining,
            "step_start_time": self.step_start_time
        }

    def _estimate_remaining_time(self) -> Optional[str]:
        """估算剩余时间"""
        if self.current_step == AnalysisStep.COMPLETED:
            return None

        # 计算当前步骤剩余时间
        min_time, max_time = self.step_estimates.get(self.current_step, (0, 0))
        step_elapsed = time.time() - self.step_start_time
        step_remaining = max(0, (min_time + max_time) / 2 - step_elapsed)

        # 计算后续步骤时间
        remaining_steps_time = 0
        for step in AnalysisStep:
            if step.value > self.current_step.value:
                min_t, max_t = self.step_estimates.get(step, (0, 0))
                remaining_steps_time += (min_t + max_t) / 2

        total_remaining = step_remaining + remaining_steps_time

        if total_remaining > 0:
            if total_remaining < 60:
                return f"{int(total_remaining)}秒"
            else:
                minutes = int(total_remaining // 60)
                seconds = int(total_remaining % 60)
                return f"{minutes}分{seconds}秒"

        return None

    def complete(self):
        """标记分析完成"""
        self.update_step(AnalysisStep.COMPLETED, 100.0)
        logger.info(
            "分析完成",
            request_id=self.request_id,
            total_time=time.time() - self.start_time
        )

# 装饰器：为分析函数添加进度跟踪
def with_progress_tracking(request_id: str):
    """
    装饰器：为分析函数添加进度跟踪

    Args:
        request_id: 请求ID
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            tracker = ProgressTracker(request_id)
            try:
                # 在这里可以添加进度回调逻辑
                result = await func(*args, **kwargs)
                tracker.complete()
                return result
            except Exception as e:
                logger.error(
                    "分析过程中出现错误",
                    request_id=request_id,
                    error=str(e),
                    current_step=tracker.current_step.value
                )
                raise
            finally:
                # 延迟清理跟踪器（让用户有时间查看最终状态）
                asyncio.create_task(
                    asyncio.sleep(300),  # 5分钟后清理
                    ProgressTracker.remove_tracker(request_id)
                )
        return wrapper
    return decorator

# 全局进度跟踪管理器
class ProgressManager:
    """进度管理器"""

    @staticmethod
    def get_all_active_progress() -> Dict[str, Dict[str, Any]]:
        """获取所有活跃的进度"""
        return {
            request_id: tracker.get_status()
            for request_id, tracker in ProgressTracker._active_trackers.items()
        }

    @staticmethod
    def get_progress_summary() -> Dict[str, Any]:
        """获取进度统计摘要"""
        trackers = ProgressTracker._active_trackers
        total_count = len(trackers)

        if total_count == 0:
            return {
                "total_active": 0,
                "by_step": {},
                "average_progress": 0.0
            }

        # 按步骤统计
        by_step = {}
        total_progress = 0.0

        for tracker in trackers.values():
            step = tracker.current_step.value
            by_step[step] = by_step.get(step, 0) + 1
            total_progress += tracker.overall_progress

        average_progress = total_progress / total_count

        return {
            "total_active": total_count,
            "by_step": by_step,
            "average_progress": round(average_progress, 1)
        }