# 🐳 Docker 架构说明

项目包含两个不同的Dockerfile，分别用于不同的使用场景。

## 📋 Dockerfile 对比

### 1. 根目录 Dockerfile - CLI工具镜像
**文件路径**: `./Dockerfile`
**镜像名称**: `allinone`
**用途**: 传统命令行工具（v1.0）

#### 特点
- 🎯 **单一用途**: 只提供CLI命令行功能
- 📦 **轻量级**: 不包含Web服务组件
- 🔄 **向后兼容**: 保持原有CLI接口
- 🚫 **已弃用**: 推荐使用API服务

#### 启动方式
```bash
# 构建镜像
docker build -t allinone -f ./Dockerfile .

# 运行CLI命令
docker run -it allinone --out-dir /output /input/audio.wav
```

#### 入口点
```dockerfile
ENTRYPOINT ["python", "-m", "allin1.cli"]
```

---

### 2. API目录 Dockerfile - RESTful API镜像
**文件路径**: `./api/Dockerfile`
**镜像名称**: `music-analysis-api`
**用途**: 现代化API服务（v2.0）⭐ **推荐**

#### 特点
- 🌐 **完整API**: 提供RESTful API服务
- 📊 **进度跟踪**: 实时分析进度反馈
- 🔄 **异步处理**: 支持后台任务处理
- 🛡️ **企业级**: 健康检查、错误处理、监控
- 🍎 **Apple Silicon优化**: 专为Mac M系列优化

#### 启动方式
```bash
# 使用Docker Compose (推荐)
docker-compose up --build

# 或直接构建API镜像
docker build -f ./api/Dockerfile -t music-analysis-api .
```

#### 入口点
```dockerfile
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🏗️ 架构对比

| 特性 | CLI Dockerfile | API Dockerfile |
|------|----------------|----------------|
| **版本** | v1.0 (传统) | v2.0 (现代) ⭐ |
| **接口** | 命令行 | RESTful API |
| **功能** | 单次分析 | 同步/异步/批量分析 |
| **进度反馈** | ❌ 无 | ✅ 实时进度 |
| **Web界面** | ❌ 无 | ✅ API文档 |
| **并发支持** | ❌ 单任务 | ✅ 多任务 |
| **健康检查** | ❌ 无 | ✅ 内置 |
| **Apple Silicon优化** | ❌ 基础 | ✅ 专门优化 |
| **推荐使用** | ❌ 备用 | ✅ 主要推荐 |

## 📁 文件结构

```
all-in-one-docker-cpu-apple-silicon/
├── Dockerfile                 # CLI工具镜像 (v1.0)
├── api/
│   └── Dockerfile            # API服务镜像 (v2.0) ⭐
├── docker-compose.yml        # API服务编排
├── scripts/
│   ├── build-cli.sh         # CLI构建脚本
│   └── build-api.sh         # API构建脚本 ⭐
└── start-api.sh             # API一键启动 ⭐
```

## 🚀 使用建议

### 新项目/现代应用
```bash
# 推荐：使用API服务
./start-api.sh
# 或
docker-compose up --build
```

### 传统CLI工具集成
```bash
# 备用：使用CLI镜像（不推荐）
./scripts/build-cli.sh
```

### 开发和测试
```bash
# 开发环境
docker-compose up --build

# 生产环境
docker-compose --profile production up -d
```

## 🔧 构建脚本

### build-cli.sh
- **用途**: 构建传统CLI镜像
- **状态**: 备用，向后兼容
- **输出**: `allinone:latest`

### build-api.sh
- **用途**: 构建现代API镜像
- **状态**: 主要推荐
- **输出**: `music-analysis-api:latest`

## 📦 镜像大小对比

| 镜像 | 大小 | 用途 |
|------|------|------|
| `allinone` | ~1.8GB | CLI工具 |
| `music-analysis-api` | ~2.2GB | API服务 |

## 🔄 迁移路径

### 从CLI迁移到API
1. **停止CLI容器** (如果正在运行)
2. **启动API服务**:
   ```bash
   ./start-api.sh
   ```
3. **更新客户端代码**:
   ```python
   # 旧CLI方式
   import allin1
   result = allin1.analyze('audio.wav')

   # 新API方式
   import requests
   response = requests.post(
       'http://localhost:8193/api/analyze/sync',
       files={'file': open('audio.wav', 'rb')}
   )
   result = response.json()['data']
   ```

## ⚠️ 重要说明

1. **不兼容性**: CLI和API是不同的接口，无法直接替换
2. **资源使用**: API镜像稍大，但提供更多功能
3. **端口冲突**: CLI无端口，API使用8000端口
4. **推荐策略**: 新项目使用API，现有CLI可继续使用

## 🔮 未来规划

- **CLI镜像**: 保持向后兼容，但不再主动开发
- **API镜像**: 持续优化和功能增强
- **统一构建**: 未来可能考虑单一镜像支持多种模式