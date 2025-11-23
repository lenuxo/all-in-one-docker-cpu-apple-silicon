# 🎵 All-In-One Music Structure Analyzer

[![arXiv](https://img.shields.io/badge/arXiv-2307.16425-B31B1B)](http://arxiv.org/abs/2307.16425/)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-f9f107)](https://huggingface.co/spaces/taejunkim/all-in-one/)
[![PyPI - Version](https://img.shields.io/pypi/v/allin1.svg)](https://pypi.org/project/allin1)
[![API Status](https://img.shields.io/badge/API-v2.0-blue)]()

基于深度学习的音乐结构分析工具，支持**RESTful API v2.0**、**Python库**和**CLI**三种使用方式。

## 💻 系统要求

### ⚠️ 重要说明
本项目**仅支持Mac M系列芯片设备**（M1/M2/M3/M4等），不具有跨平台兼容性。

### 硬件要求
- **设备**: Mac M系列芯片（Apple Silicon）
- **内存**: 最低8GB，推荐16GB+
- **存储**: 至少10GB可用空间
- **网络**: 用于下载依赖和模型文件

### 软件要求
- **macOS**: 11.0+（Big Sur或更高版本）
- **Docker**: 20.10+（支持Apple Silicon）
- **Docker Compose**: 2.0+

### 性能参考
- **M1芯片**: 45-90秒/曲（取决于音频长度）
- **M2/M3芯片**: 30-60秒/曲（优化性能）
- **内存使用**: 峰值2-4GB（取决于音频文件大小）

## 🚀 快速开始

### API服务（推荐）

```bash
# 一键启动
./start-api.sh

# 手动启动
docker-compose up --build

# 访问
# API文档: http://localhost:8193/docs
# 健康检查: http://localhost:8193/api/system/health
```

### Python库

```bash
pip install allin1
import allin1
result = allin1.analyze('your_audio.wav')
```

### CLI工具

```bash
./scripts/build-cli.sh
docker run -it allinone your_audio.wav
```

## 📋 API架构 v2.0

### 三种分析模式

| 模式 | 端点 | 适用场景 | 特点 |
|------|------|----------|------|
| **同步分析** | `POST /api/analyze/sync` | 脚本、后台任务 | ⚡ 一次调用返回结果 |
| **异步分析** | `POST /api/analyze/async` | Web应用、移动端 | 📊 详细进度跟踪 |
| **批量分析** | `POST /api/analyze/batch` | 企业级批量处理 | 🔀 多文件并行处理 |

### 核心特性
- 📊 **10步实时进度跟踪**：从初始化到完成的详细分析过程
- 💾 **内存文件处理**：避免磁盘空间膨胀，自动清理
- 🛡️ **企业级可靠性**：完整错误处理、任务管理、并发控制
- 📈 **系统监控**：内存、任务状态实时监控
- 🎯 **灵活配置**：多种模型、输出格式支持
- 🍎 **Apple Silicon优化**：专为Mac M系列芯片优化

## 🔧 API使用示例

### 同步分析
```bash
curl -X POST "http://localhost:8193/api/analyze/sync" \
  -F "file=@music.wav" \
  -F "model=harmonix-all" \
  -F "visualize=true"
```

### 异步分析（带进度）
```bash
# 1. 提交任务
curl -X POST "http://localhost:8193/api/analyze/async" \
  -F "file=@music.wav" \
  -F "model=harmonix-all"

# 2. 查询进度
curl -X GET "http://localhost:8193/api/progress/{request_id}"
```

### 批量分析
```bash
curl -X POST "http://localhost:8193/api/analyze/batch" \
  -F "files=@song1.wav" \
  -F "files=@song2.mp3" \
  -F "priority=1"
```

## 📊 分析结果

```json
{
  "bpm": 120.5,
  "beats": [0.33, 0.75, 1.14, 1.56],
  "downbeats": [0.33, 1.94, 3.53],
  "beat_positions": [1, 2, 3, 4, 1, 2, 3, 4],
  "segments": [
    {"start": 0.0, "end": 0.33, "label": "start"},
    {"start": 0.33, "end": 13.13, "label": "intro"},
    {"start": 13.13, "end": 37.53, "label": "chorus"}
  ]
}
```

**段落标签**: `start`, `intro`, `verse`, `chorus`, `bridge`, `outro`, `break`, `inst`, `solo`

## 🛠️ 项目结构

```
├── start-api.sh          # 🎯 一键启动脚本
├── scripts/              # 构建脚本目录
│   ├── build-api.sh      # API服务构建
│   ├── build-cli.sh      # CLI工具构建
│   └── common.sh         # 通用函数
├── api/                  # API服务代码
│   ├── endpoints/        # API端点
│   ├── models/           # 数据模型
│   ├── services/         # 业务逻辑
│   └── utils/            # 工具函数
├── src/                  # allin1核心库
├── docker-compose.yml    # 部署配置
└── Dockerfile            # CLI Dockerfile
```

## ⚙️ 构建脚本

### 启动脚本
```bash
./start-api.sh          # 启动API服务
./start-api.sh --stop    # 停止服务
./start-api.sh --logs    # 查看日志
./start-api.sh --check   # 检查依赖
```

### 构建脚本
```bash
./scripts/build-api.sh   # 构建API镜像
./scripts/build-cli.sh   # 构建CLI镜像
```

## 🎯 模型选择

| 模型 | 精度 | 速度 | 描述 |
|------|------|------|------|
| `harmonix-all` | 最高 | 中等 | 集成8个模型的平均结果（推荐） |
| `harmonix-fold0-7` | 高 | 快 | 单个折模型 |

## 📏 限制

- **并发任务**: 最多5个
- **支持格式**: WAV（推荐）、MP3
- **文件大小**: 无限制（由核心库和系统资源决定）
- **音频时长**: 无限制（由核心库和系统资源决定）

## 🔧 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 内存：最低4GB，推荐8GB+
- 存储：至少10GB

## 📝 API端点

### 分析API
```
POST /api/analyze/sync           # 同步分析
POST /api/analyze/async          # 异步分析
POST /api/analyze/batch          # 批量分析
GET  /api/analyze/result/{task_id}  # 获取结果
```

### 监控API
```
GET /api/progress/{request_id}    # 查询进度
GET /api/system/health           # 健康检查
GET /api/system/info              # 系统信息
```

### 文件管理
```
POST /api/files/upload            # 文件上传
GET  /api/files/download/{id}     # 文件下载
```

## 🔍 错误处理

常见错误代码：
- `INVALID_FORMAT` (422) - 不支持的文件格式
- `FILE_TOO_LARGE` (413) - 文件超过50MB
- `AUDIO_DURATION_EXCEEDED` (413) - 音频超过10分钟
- `TASK_NOT_FOUND` (404) - 任务不存在

## 📱 客户端集成

### JavaScript
```typescript
class MusicAnalysisAPI {
  async analyzeSync(file: File, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    return await fetch('http://localhost:8193/api/analyze/sync', {
      method: 'POST', body: formData
    }).then(r => r.json());
  }
}
```

### Python
```python
import requests

def analyze_audio(file_path, **options):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        return requests.post(
            'http://localhost:8193/api/analyze/sync',
            files=files, data=options
        ).json()
```

## 🔧 开发

### Python库使用
```python
import allin1

# 分析单文件
result = allin1.analyze('audio.wav')

# 批量分析
results = allin1.analyze(['file1.wav', 'file2.mp3'])

# 包含可视化
result = allin1.analyze('audio.wav', visualize=True, sonify=True)
```

### CLI选项
```bash
allin1 your_audio.wav \
  --model harmonix-all \
  --visualize \
  --sonify \
  --activ \
  --embed
```

## 📚 详细文档

- **API完整文档**: [API_README.md](API_README.md)
- **Apple Silicon兼容性**: [APPLE_SILICON.md](APPLE_SILICON.md)
- **Docker架构说明**: [DOCKER_ARCHITECTURE.md](DOCKER_ARCHITECTURE.md)
- **构建脚本说明**: [scripts/README.md](scripts/README.md)
- **更新日志**: [CHANGELOG.md](CHANGELOG.md)

## ⚡ 性能

- **精度**: 节拍检测误差<70ms
- **速度**: M1芯片45-90秒/曲，M2/M3芯片30-60秒/曲
- **格式**: WAV（推荐），MP3（可能有20-40ms时差）
- **内存**: 峰值使用2-4GB
- **并发**: 支持2-4个并发分析任务

## 🎵 可视化与音频化

```bash
# 生成可视化图表
allin1 -v your_audio.wav

# 生成音频化标注
allin1 -s your_audio.wav

# API中启用
visualize=true, sonify=true
```

## 🔬 高级功能

### 原始数据和嵌入
```bash
# CLI
allin1 --activ --embed your_audio.wav

# API
include_activations=true, include_embeddings=true
```

### 激活数据格式
- `beat`: 节拍激活 (shape: `[time_steps]`)
- `downbeat`: 强拍激活 (shape: `[time_steps]`)
- `segment`: 段落边界激活 (shape: `[time_steps]`)
- `label`: 段落标签激活 (shape: `[10, time_steps]`)

## 🏗️ 部署

### 生产环境
```yaml
# docker-compose.prod.yml
services:
  music-analysis-api:
    image: music-analysis-api:latest
    deploy:
      replicas: 2
      resources:
        limits: {memory: 4G}
    environment:
      - ENV=production
      - MAX_CONCURRENT_TASKS=4
    # Apple Silicon优化配置
    platform: linux/arm64
```

### 环境变量
```bash
ENV=development
PORT=8193
LOG_LEVEL=info
MAX_FILE_SIZE_MB=50
MAX_AUDIO_DURATION_SECONDS=600
MAX_CONCURRENT_TASKS=5
```

## 📞 技术支持

- **API文档**: http://localhost:8193/docs
- **ReDoc**: http://localhost:8193/redoc
- **健康检查**: http://localhost:8193/api/system/health

---

## Citation

If you use this package for research, please cite:

```bibtex
@inproceedings{taejun2023allinone,
  title={All-In-One Metrical And Functional Structure Analysis With Neighborhood Attentions on Demixed Audio},
  author={Kim, Taejun and Nam, Juhan},
  booktitle={IEEE Workshop on Applications of Signal Processing to Audio and Acoustics (WASPAA)},
  year={2023}
}
```