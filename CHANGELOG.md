# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2024-11-23

### 🚀 Major - 全新API架构重新设计

**从简单CLI工具升级为企业级RESTful API服务**

#### ✨ 新增功能
- **🎵 三种专业API模式**: 同步分析、异步分析（带进度）、批量分析
- **📊 实时进度跟踪**: 10步详细分析过程反馈
- **💾 内存文件处理**: 避免磁盘空间膨胀，自动清理
- **🛡️ 企业级可靠性**: 完整错误处理、任务管理、并发控制
- **📈 系统监控**: CPU、内存、任务状态实时监控

#### 🔧 新API端点
```
POST /api/analyze/sync           # 同步分析
POST /api/analyze/async          # 异步分析（带进度）
POST /api/analyze/batch          # 批量分析
GET  /api/progress/{request_id}    # 查询进度
GET  /api/system/health           # 健康检查
POST /api/files/upload            # 文件上传
```

#### 🔄 向后兼容性
- 原有CLI接口完全兼容
- Python库 `pip install allin1` 继续可用
- Docker镜像 `allinone` 继续支持

## [1.1.0] - 2023-10-10

### Added
- Docker容器化支持
- API服务功能预览

---

*基于 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) 和 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)*