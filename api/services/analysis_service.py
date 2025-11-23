"""
音频分析服务
集成allin1库，提供音乐分析功能
"""

import os
import sys
import time
import asyncio
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import json

# 添加项目根目录到Python路径，以便导入allin1
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import allin1
import structlog
from ..models import (
    AnalysisRequest,
    AnalysisResult,
    BatchAnalysisRequest,
    FileLinks,
    BatchResultResponse,
    TaskStatus
)
from ..utils import generate_unique_filename, ensure_directory
from .progress_tracker import ProgressTracker, AnalysisStep

logger = structlog.get_logger()

class AnalysisService:
    """音频分析服务"""

    def __init__(self):
        self.upload_dir = Path("api/static/uploads")
        self.results_dir = Path("api/static/results")
        self.temp_dir = Path("api/temp")

        # 批量任务管理
        self.batch_tasks: Dict[str, Dict] = {}

        # 确保目录存在
        asyncio.create_task(ensure_directory(self.upload_dir))
        asyncio.create_task(ensure_directory(self.results_dir))
        asyncio.create_task(ensure_directory(self.temp_dir))

    async def analyze_single_file_with_progress(
        self,
        file_path: Path,
        request: AnalysisRequest,
        request_id: str
    ) -> Tuple[AnalysisResult, Optional[FileLinks]]:
        """
        分析单个音频文件（带进度跟踪）

        Args:
            file_path: 音频文件路径
            request: 分析请求参数
            request_id: 请求ID

        Returns:
            Tuple[AnalysisResult, Optional[FileLinks]]: 分析结果和文件链接
        """
        # 创建进度跟踪器
        tracker = ProgressTracker(request_id)

        try:
            # 强制使用CPU设备，忽略请求中的device参数
            device = "cpu"
            logger.info(
                "开始分析音频文件（带进度跟踪）",
                request_id=request_id,
                file_path=str(file_path),
                model=request.model.value,
                device=device
            )

            # 步骤1：初始化
            tracker.update_step(AnalysisStep.INITIALIZING, 0)
            await asyncio.sleep(0.1)  # 让进度更新有时间传播
            tracker.update_step_progress(100)

            # 步骤2：准备输出目录
            tracker.update_step(AnalysisStep.INITIALIZING, 50)
            output_dir = self.results_dir / f"analysis_{request_id}"
            await ensure_directory(output_dir)
            tracker.update_step_progress(100)

            # 步骤3：加载模型（模拟进度）
            tracker.update_step(AnalysisStep.LOADING_MODEL, 0)
            # 模拟模型加载过程
            for i in range(0, 101, 10):
                tracker.update_step_progress(i)
                await asyncio.sleep(0.1)  # 模拟加载时间

            # 步骤4：构建allin1分析参数
            tracker.update_step(AnalysisStep.AUDIO_SEPARATION, 0)
            kwargs = {
                "paths": [str(file_path)],
                "model": request.model.value,
                "device": device,
                "out_dir": str(output_dir),
                "visualize": output_dir if request.visualize else False,
                "sonify": output_dir if request.sonify else False,
                "include_activations": request.include_activations,
                "include_embeddings": request.include_embeddings,
                "overwrite": request.overwrite,
                "multiprocess": False  # 在API环境中使用单进程
            }

            # 执行分析（这是最耗时的部分）
            tracker.update_step_progress(50)

            # 由于allin1.analyze()是同步的，我们在单独的线程中运行
            loop = asyncio.get_event_loop()

            # 在后台更新进度，让用户知道分析正在进行
            async def update_progress_during_analysis():
                progress_values = [60, 70, 80, 90]
                for progress in progress_values:
                    await asyncio.sleep(2)  # 每2秒更新一次
                    tracker.update_step_progress(progress)
                    if tracker.current_step != AnalysisStep.AUDIO_SEPARATION:
                        break

            # 启动进度更新任务
            progress_task = asyncio.create_task(update_progress_during_analysis())

            try:
                # 执行实际的分析
                results = await loop.run_in_executor(
                    None,
                    lambda: allin1.analyze(**kwargs)
                )
                progress_task.cancel()
            except asyncio.CancelledError:
                pass

            tracker.update_step_progress(100)

            # 步骤5：处理结果
            tracker.update_step(AnalysisStep.GENERATING_RESULTS, 0)
            analysis_result = results[0] if isinstance(results, list) else results
            tracker.update_step_progress(50)

            # 转换为我们的响应格式
            analysis_result_data = self._convert_allin1_result(analysis_result, file_path)
            tracker.update_step_progress(100)

            # 步骤6：生成文件下载链接
            tracker.update_step(AnalysisStep.SAVING_OUTPUTS, 0)
            file_links = self._generate_file_links(
                file_path,
                output_dir,
                request,
                request_id
            )
            tracker.update_step_progress(100)

            # 完成
            tracker.complete()

            logger.info(
                "音频文件分析完成（带进度跟踪）",
                request_id=request_id,
                duration=analysis_result_data.duration,
                segment_count=analysis_result_data.segment_count,
                total_time=time.time() - tracker.start_time
            )

            return analysis_result_data, file_links

        except Exception as e:
            logger.error(
                "音频文件分析失败（带进度跟踪）",
                request_id=request_id,
                file_path=str(file_path),
                error=str(e),
                current_step=tracker.current_step.value if 'tracker' in locals() else "unknown"
            )
            # 确保在错误情况下也清理进度跟踪器
            if 'tracker' in locals():
                ProgressTracker.remove_tracker(request_id)
            raise

    async def analyze_single_file(
        self,
        file_path: Path,
        request: AnalysisRequest,
        request_id: str
    ) -> Tuple[AnalysisResult, Optional[FileLinks]]:
        """
        分析单个音频文件（兼容性方法）

        这个方法保持向后兼容，内部调用带进度跟踪的版本
        """
        return await self.analyze_single_file_with_progress(file_path, request, request_id)

    def _convert_allin1_result(self, result, original_path: Path) -> AnalysisResult:
        """
        将allin1分析结果转换为我们的格式

        Args:
            result: allin1分析结果
            original_path: 原始文件路径

        Returns:
            AnalysisResult: 转换后的结果
        """
        # 转换segments
        segments = []
        for segment in result.segments:
            segments.append({
                "start": float(segment.start),
                "end": float(segment.end),
                "label": segment.label
            })

        # 构建结果数据
        result_data = AnalysisResult(
            path=str(original_path),
            bpm=float(result.bpm),
            beats=[float(beat) for beat in result.beats],
            downbeats=[float(downbeat) for downbeat in result.downbeats],
            beat_positions=[int(pos) for pos in result.beat_positions],
            segments=segments
        )

        # 添加激活数据（如果有）
        if hasattr(result, 'activations') and result.activations:
            result_data.activations = {
                "beat": result.activations.get("beat", []).tolist() if hasattr(result.activations.get("beat", []), "tolist") else result.activations.get("beat", []),
                "downbeat": result.activations.get("downbeat", []).tolist() if hasattr(result.activations.get("downbeat", []), "tolist") else result.activations.get("downbeat", []),
                "segment": result.activations.get("segment", []).tolist() if hasattr(result.activations.get("segment", []), "tolist") else result.activations.get("segment", []),
                "label": result.activations.get("label", []).tolist() if hasattr(result.activations.get("label", []), "tolist") else result.activations.get("label", [])
            }

        # 添加嵌入数据（如果有）
        if hasattr(result, 'embeddings') and result.embeddings is not None:
            result_data.embeddings = result.embeddings.flatten().tolist() if hasattr(result.embeddings, "flatten") else result.embeddings

        return result_data

    def _generate_file_links(
        self,
        file_path: Path,
        output_dir: Path,
        request: AnalysisRequest,
        request_id: str
    ) -> FileLinks:
        """
        生成文件下载链接

        Args:
            file_path: 原始文件路径
            output_dir: 输出目录
            request: 分析请求
            request_id: 请求ID

        Returns:
            FileLinks: 文件下载链接
        """
        file_links = FileLinks()
        base_filename = file_path.stem

        # 可视化文件
        if request.visualize:
            viz_file = output_dir / f"{base_filename}.pdf"
            if viz_file.exists():
                file_links.visualization = f"/api/files/download/analysis_{request_id}/{viz_file.name}"

        # 音频化文件
        if request.sonify:
            sonif_file = output_dir / f"{base_filename}.sonif.wav"
            if sonif_file.exists():
                file_links.sonification = f"/api/files/download/analysis_{request_id}/{sonif_file.name}"

        # JSON结果文件
        json_file = output_dir / f"{base_filename}.json"
        if json_file.exists():
            file_links.json_result = f"/api/files/download/analysis_{request_id}/{json_file.name}"

        # 激活数据文件
        if request.include_activations:
            activ_file = output_dir / f"{base_filename}.activ.npz"
            if activ_file.exists():
                file_links.activations = f"/api/files/download/analysis_{request_id}/{activ_file.name}"

        # 嵌入向量文件
        if request.include_embeddings:
            embed_file = output_dir / f"{base_filename}.embed.npy"
            if embed_file.exists():
                file_links.embeddings = f"/api/files/download/analysis_{request_id}/{embed_file.name}"

        return file_links

    async def create_batch_task(
        self,
        files: List[Any],  # UploadFile objects
        request: BatchAnalysisRequest,
        background_tasks: Any
    ) -> str:
        """
        创建批量分析任务

        Args:
            files: 上传的文件列表
            request: 批量分析请求
            background_tasks: FastAPI后台任务

        Returns:
            str: 任务ID
        """
        task_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        # 保存上传的文件
        file_paths = []
        for file in files:
            unique_filename = generate_unique_filename(file.filename or "audio")
            upload_path = self.upload_dir / unique_filename

            with open(upload_path, "wb") as f:
                content = await file.read()
                f.write(content)

            file_paths.append(upload_path)

        # 创建任务记录
        self.batch_tasks[task_id] = {
            "id": task_id,
            "status": "pending",
            "progress": 0.0,
            "current_file": None,
            "completed_files": [],
            "failed_files": [],
            "total_files": len(file_paths),
            "file_paths": file_paths,
            "request": request,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "results": {},
            "estimated_time": f"{len(file_paths) * 30}-{len(file_paths) * 60}秒"
        }

        # 添加后台任务
        background_tasks.add_task(self._process_batch_task, task_id)

        logger.info(
            "批量分析任务已创建",
            task_id=task_id,
            file_count=len(file_paths),
            priority=request.priority
        )

        return task_id

    async def _process_batch_task(self, task_id: str):
        """
        处理批量分析任务（后台运行）

        Args:
            task_id: 任务ID
        """
        if task_id not in self.batch_tasks:
            return

        task = self.batch_tasks[task_id]
        file_paths = task["file_paths"]
        request = task["request"]

        try:
            # 更新任务状态为处理中
            task["status"] = "processing"
            task["updated_at"] = datetime.now().isoformat()

            total_files = len(file_paths)

            for i, file_path in enumerate(file_paths):
                try:
                    # 更新当前处理文件
                    task["current_file"] = file_path.name
                    task["progress"] = (i / total_files) * 100
                    task["updated_at"] = datetime.now().isoformat()

                    # 创建单个文件分析请求（强制使用CPU）
                    single_request = AnalysisRequest(
                        model=request.model,
                        device=DeviceType.CPU,  # 强制使用CPU
                        visualize=request.visualize,
                        sonify=request.sonify,
                        include_activations=request.include_activations,
                        include_embeddings=request.include_embeddings,
                        overwrite=request.overwrite
                    )

                    # 分析文件
                    result_data, file_links = await self.analyze_single_file(
                        file_path,
                        single_request,
                        f"{task_id}_{i}"
                    )

                    # 保存结果
                    task["results"][file_path.name] = {
                        "data": result_data,
                        "files": file_links
                    }

                    # 添加到已完成列表
                    task["completed_files"].append(file_path.name)

                    logger.info(
                        "批量任务文件处理完成",
                        task_id=task_id,
                        file_name=file_path.name,
                        progress=f"{((i+1)/total_files)*100:.1f}%"
                    )

                except Exception as e:
                    logger.error(
                        "批量任务文件处理失败",
                        task_id=task_id,
                        file_name=file_path.name,
                        error=str(e)
                    )
                    task["failed_files"].append(file_path.name)

            # 任务完成
            task["status"] = "completed"
            task["progress"] = 100.0
            task["current_file"] = None
            task["updated_at"] = datetime.now().isoformat()

            logger.info(
                "批量分析任务完成",
                task_id=task_id,
                completed_count=len(task["completed_files"]),
                failed_count=len(task["failed_files"])
            )

        except Exception as e:
            logger.error(
                "批量分析任务处理失败",
                task_id=task_id,
                error=str(e)
            )
            task["status"] = "failed"
            task["updated_at"] = datetime.now().isoformat()

    async def get_batch_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取批量任务状态

        Args:
            task_id: 任务ID

        Returns:
            Optional[Dict]: 任务状态和结果
        """
        if task_id not in self.batch_tasks:
            return None

        task = self.batch_tasks[task_id]

        # 计算预计剩余时间
        estimated_remaining = None
        if task["status"] == "processing" and task["progress"] > 0:
            completed_count = len(task["completed_files"]) + len(task["failed_files"])
            remaining_count = task["total_files"] - completed_count

            if completed_count > 0:
                elapsed_time = (datetime.now() - datetime.fromisoformat(task["created_at"])).total_seconds()
                avg_time_per_file = elapsed_time / completed_count
                estimated_seconds = remaining_count * avg_time_per_file
                estimated_remaining = f"{int(estimated_seconds // 60)}-{int((estimated_seconds // 60) + 1)}分钟"

        # 构建响应
        response = {
            "success": True,
            "task_id": task_id,
            "status": TaskStatus(
                task_id=task_id,
                status=task["status"],
                progress=task["progress"],
                current_file=task["current_file"],
                completed_files=task["completed_files"],
                failed_files=task["failed_files"],
                estimated_remaining=estimated_remaining,
                created_at=task["created_at"],
                updated_at=task["updated_at"]
            ).dict()
        }

        # 如果任务完成，添加结果
        if task["status"] == "completed":
            results = []
            all_files = {}

            for file_name, result_data in task["results"].items():
                results.append(result_data["data"])
                if result_data["files"]:
                    all_files[file_name] = result_data["files"]

            response["results"] = results
            response["files"] = all_files
            response["total_processing_time"] = (
                datetime.fromisoformat(task["updated_at"]) -
                datetime.fromisoformat(task["created_at"])
            ).total_seconds()

        return response

    async def cancel_batch_task(self, task_id: str) -> bool:
        """
        取消批量任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        if task_id not in self.batch_tasks:
            return False

        task = self.batch_tasks[task_id]

        if task["status"] in ["pending", "processing"]:
            task["status"] = "cancelled"
            task["updated_at"] = datetime.now().isoformat()

            logger.info("批量任务已取消", task_id=task_id)
            return True

        return False