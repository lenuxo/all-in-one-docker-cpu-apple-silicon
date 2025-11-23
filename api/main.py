"""
音乐分析API主应用
基于FastAPI框架，提供音频文件分析服务
"""

import os
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import structlog

from .endpoints import (
    analysis_sync,      # 同步分析API
    analysis_async,     # 异步分析API
    analysis_batch,      # 批量分析API
    files,               # 文件管理API
    progress,            # 进度查询API
    system,              # 系统监控API
    storage_monitor      # 存储监控API
)
from .models import ErrorResponse

# 配置日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# 应用启动时间
START_TIME = time.time()

def custom_openapi():
    """自定义OpenAPI配置"""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title="音乐分析API",
        version="1.0.0",
        description="""
# 🎵 音乐分析API 完整使用指南

## 概述
本API提供专业的音频结构分析服务，基于深度学习模型识别音乐中的节拍、段落等音乐元素。

## 快速开始
1. 访问 `/api/analyze` 端点上传音频文件
2. 选择分析模型和参数
3. 获取JSON格式的分析结果

## 支持的功能
- ✅ 节拍检测 (BPM, 节拍位置)
- ✅ 段落分析 (边界和标签识别)
- ✅ 可视化图表生成
- ✅ 音频化标注生成
- ✅ 批量文件处理
- ✅ 原始数据导出

## 性能指标
- **精度**: 节拍检测误差<70ms
- **速度**: CPU 30-60秒/曲，GPU 10-20秒/曲
- **格式**: WAV (推荐), MP3

## 使用限制
- 文件大小: ≤ 50MB
- 音频时长: ≤ 10分钟
- 并发请求: 最多5个

## 支持的音频格式

### WAV格式 (推荐)
- **采样率**: 建议44.1kHz或更高
- **位深**: 16-bit或24-bit
- **声道**: 单声道或立体声
- **精度**: 最高精度，无时差问题

### MP3格式
- **比特率**: 建议128kbps或更高
- **注意事项**: 可能有20-40ms时差
- **建议**: 先转换为WAV格式以获得最佳精度

## 分析结果说明

### 节拍分析
- **BPM**: 每分钟节拍数
- **beats**: 所有节拍时间点（秒）
- **downbeats**: 强拍时间点（小节第一拍）
- **beat_positions**: 节拍在节拍循环中的位置

### 段落分析
- **start**: 段落开始时间
- **end**: 段落结束时间
- **label**: 段落类型标签
  - `start`: 开始部分
  - `intro`: 前奏
  - `verse`: 主歌
  - `chorus`: 副歌
  - `bridge`: 桥段
  - `outro`: 尾奏

## 错误代码说明
- `INVALID_FORMAT`: 不支持的文件格式
- `FILE_TOO_LARGE`: 文件大小超限
- `AUDIO_DURATION_EXCEEDED`: 音频时长超限
- `PROCESSING_ERROR`: 分析处理错误
- `MODEL_NOT_LOADED`: 模型未加载
- `RATE_LIMIT_EXCEEDED`: 请求频率超限

---

*API版本: 1.0.0 | 最后更新: 2024年11月*
        """,
        routes=app.routes,
        servers=[
            {
                "url": f"http://localhost:{os.getenv('PORT', '8193')}",
                "description": "开发环境"
            },
            {
                "url": "https://api.music-analysis.com",
                "description": "生产环境"
            }
        ]
    )

    # 添加标签分组 - 重新组织的文档结构
    openapi_schema["tags"] = [
        {
            "name": "🎵 同步分析",
            "description": "简单直接的音频分析API，一次调用返回结果，适合脚本和后台任务"
        },
        {
            "name": "🔄 异步分析",
            "description": "带进度跟踪的音频分析API，支持实时进度反馈，适合交互式应用"
        },
        {
            "name": "📁 批量分析",
            "description": "多文件批量处理API，支持任务管理和详细进度跟踪"
        },
        {
            "name": "📂 文件管理",
            "description": "文件上传、下载和管理相关的API"
        },
        {
            "name": "📊 进度查询",
            "description": "实时进度跟踪和任务状态查询API"
        },
        {
            "name": "❤️ 系统监控",
            "description": "系统状态、健康检查和服务监控API"
        },
        {
            "name": "💾 存储监控",
            "description": "临时文件存储管理和清理API"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# 创建FastAPI应用
app = FastAPI(
    title="音乐分析API",
    description="专业的音频结构分析服务",
    version="1.0.0",
    docs_url=None,  # 禁用默认的Swagger UI
    redoc_url=None,  # 禁用默认的Redoc，我们将自定义
    openapi_url="/openapi.json"
)

# 自定义RapiDoc HTML模板
RAPIDOC_HTML = """
<!DOCTYPE html>
<html>
  <head>
    <title>音乐分析API - RapiDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/rapidoc/dist/rapidoc-min.min.js"></script>
    <style>
      body {
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      }
      rapi-doc {
        height: 100vh;
        width: 100%;
      }
    </style>
  </head>
  <body>
    <rapi-doc
      id="rapidoc"
      spec-url="/openapi.json"
      theme="light"
      header-color="#3f51b5"
      primary-color="#3f51b5"
      load-on-render="true"
      allow-authentication="false"
      allow-server-selection="false"
      allow-api-list-style-selection="false"
      sort-endpoints-by="method"
      sort-tags-alphabetically="true"
      default-schema-tab="example"
      schema-expand-level="1"
      schema-description-expanded="true"
      allow-schema-description-expand-toggle="true"
      show-info="true"
      info-description-headings-in-navbar="true"
      show-header="true"
      show-side-nav="true"
      nav-bg-color="#f5f5f5"
      nav-text-color="#333333"
      nav-hover-bg-color="#e0e0e0"
      nav-accent-color="#3f51b5"
      regular-font="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
      mono-font="'SF Mono', Monaco, Inconsolata, 'Roboto Mono', Consolas, 'Courier New', monospace"
      font-size="large"
      render-style="read">
      <!-- 下载量统计 -->
      <slot name="footer">
        <div style="text-align: center; padding: 20px; color: #666; border-top: 1px solid #eee;">
          <p>音乐分析API v1.0.0 - 基于深度学习的音频结构分析服务</p>
        </div>
      </slot>
    </rapi-doc>
  </body>
</html>
"""

# 添加自定义路由，让 /docs 指向 RapiDoc

@app.get("/docs", include_in_schema=False)
async def custom_docs():
    """将 /docs 重定向到 RapiDoc"""
    return RedirectResponse(url="/redoc")

@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """自定义RapiDoc页面，使用CDN加载JS文件"""
    return HTMLResponse(content=RAPIDOC_HTML)

app.openapi = custom_openapi

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 静态文件服务（用于文件下载）
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# 注册路由 - 重新组织的API架构

# === 音频分析API ===
# 同步分析 - 简单直接，适合脚本和后台任务
app.include_router(analysis_sync.router, prefix="/api", tags=["🎵 同步分析"])

# 异步分析 - 带进度跟踪，适合交互式应用
app.include_router(analysis_async.router, prefix="/api", tags=["🔄 异步分析"])

# 批量分析 - 多文件处理，适合批量任务
app.include_router(analysis_batch.router, prefix="/api", tags=["📁 批量分析"])

# === 功能支持API ===
# 文件管理 - 上传下载等文件操作
app.include_router(files.router, prefix="/api/files", tags=["📂 文件管理"])

# 进度查询 - 实时进度跟踪
app.include_router(progress.router, prefix="/api/progress", tags=["📊 进度查询"])

# 系统监控 - 服务状态和健康检查
app.include_router(system.router, prefix="/api/system", tags=["❤️ 系统监控"])

# 存储监控 - 临时文件管理
app.include_router(storage_monitor.router, prefix="/api/storage", tags=["💾 存储监控"])

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("音乐分析API启动", version="1.0.0", environment=os.getenv("ENV", "development"))

    # 确保必要的目录存在
    os.makedirs("api/static/uploads", exist_ok=True)
    os.makedirs("api/static/results", exist_ok=True)
    os.makedirs("api/temp", exist_ok=True)

    logger.info("目录结构检查完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("音乐分析API关闭", uptime=time.time() - START_TIME)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加处理时间和请求头信息"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # 将请求ID添加到请求状态中
    request.state.request_id = request_id

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-API-Version"] = "1.0.0"

    # 记录请求日志
    logger.info(
        "API请求",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time,
        request_id=request_id
    )

    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    request_id = getattr(request.state, 'request_id', 'unknown')

    error_response = ErrorResponse(
        message=exc.detail,
        error_code=f"HTTP_{exc.status_code}",
        request_id=request_id
    )

    logger.warning(
        "HTTP异常",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        request_id=request_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    request_id = getattr(request.state, 'request_id', 'unknown')

    error_response = ErrorResponse(
        message="服务器内部错误",
        error_code="INTERNAL_ERROR",
        details={"exception": str(exc)},
        request_id=request_id
    )

    logger.error(
        "服务器内部错误",
        exception=str(exc),
        url=str(request.url),
        request_id=request_id
    )

    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )

@app.get("/", include_in_schema=False)
async def root():
    """根路径重定向到文档"""
    return {"message": "音乐分析API", "docs": "/docs", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )