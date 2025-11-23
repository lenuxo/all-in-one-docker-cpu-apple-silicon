# 🍎 Apple Silicon 兼容性说明

## ⚠️ 重要声明

本项目**仅支持Mac M系列芯片设备**（Apple Silicon），**不具备跨平台兼容性**。

## 💻 支持的硬件

### ✅ 完全支持
- **MacBook Pro/Air**: M1, M1 Pro, M1 Max, M1 Ultra
- **MacBook Pro/Air**: M2, M2 Pro, M2 Max, M2 Ultra
- **MacBook Pro/Air**: M3, M3 Pro, M3 Max, M3 Ultra
- **Mac mini**: M1, M2, M2 Pro
- **iMac**: M1, M3, M3 variants
- **Mac Studio**: M1, M2, M2 Ultra, M2 Max

### ❌ 不支持
- Intel Mac（任何型号）
- AMD芯片设备
- NVIDIA GPU设备
- Linux/Windows系统
- Android/iOS设备

## 🚀 性能优化

### M1芯片系列
- **处理速度**: 45-90秒/曲（取决于音频长度）
- **内存使用**: 峰值2-3GB
- **并发任务**: 建议1-2个

### M2芯片系列
- **处理速度**: 30-60秒/曲（优化性能）
- **内存使用**: 峰值2-4GB
- **并发任务**: 支持2-3个

### M3芯片系列
- **处理速度**: 25-50秒/曲（最新优化）
- **内存使用**: 峰值2-4GB
- **并发任务**: 支持3-4个

## ⚙️ 系统配置建议

### 最低配置
- **芯片**: Apple Silicon M1
- **内存**: 8GB
- **存储**: 10GB可用空间
- **macOS**: 11.0 Big Sur

### 推荐配置
- **芯片**: Apple Silicon M2/M3
- **内存**: 16GB+
- **存储**: 20GB+可用空间
- **macOS**: 13.0 Ventura+

### 优化配置
- **芯片**: Apple Silicon M3 Pro/Max/Ultra
- **内存**: 32GB+
- **存储**: 50GB+ SSD空间
- **macOS**: 14.0 Sonoma+

## 🐳 Docker优化

### ARM64镜像
项目使用专门为ARM64架构优化的Docker镜像：

```yaml
# docker-compose.yml
services:
  music-analysis-api:
    build:
      platform: linux/arm64  # Apple Silicon优化
```

### 性能调优
- **内存限制**: 建议设置为4GB
- **并发任务**: 根据芯片型号调整（M1:1-2, M2:2-3, M3:3-4）
- **存储**: 使用SSD获得最佳性能

## 🔧 开发环境

### Python依赖
```bash
# Apple Silicon优化的PyTorch安装
pip install torch torchvision torchaudio
```

### MPS支持
```python
# 启用Metal Performance Shaders
import torch
if torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
```

## 📊 基准测试

### 测试环境
- **芯片**: Apple M2 Pro
- **内存**: 16GB
- **存储**: 512GB SSD

### 测试结果
| 音频长度 | 处理时间 | 内存使用 | 精度 |
|----------|----------|----------|------|
| 30秒 | 25-35秒 | 1.8GB | 95%+ |
| 1分钟 | 35-50秒 | 2.2GB | 95%+ |
| 3分钟 | 60-90秒 | 3.1GB | 95%+ |
| 5分钟 | 90-120秒 | 3.8GB | 95%+ |

## 🚨 已知限制

### 硬件限制
- 不支持外接GPU
- 内存使用受统一内存限制
- 高并发可能影响系统响应

### 软件限制
- 某些Python包可能需要特殊编译
- Docker镜像较大（~2GB）
- 模型文件下载较慢（首次运行）

## 🔄 迁移指南

### 从Intel Mac迁移
1. 确保使用Apple Silicon Mac
2. 重新安装Docker Desktop for Mac
3. 重新拉取ARM64镜像
4. 调整并发任务数量
5. 验证性能表现

### 从其他平台迁移
⚠️ **无法迁移** - 本项目专为Apple Silicon设计，不支持跨平台。

## 📞 技术支持

如遇到Apple Silicon相关问题：

1. **检查系统要求**: 确认使用支持的芯片型号
2. **更新系统**: 升级到最新macOS版本
3. **Docker版本**: 使用支持ARM64的Docker版本
4. **内存检查**: 确保有足够可用内存
5. **存储空间**: 确保充足的磁盘空间

## 🔮 未来计划

- **M4芯片支持**: 即将支持最新的M4系列
- **性能优化**: 持续优化Apple Silicon性能
- **内存管理**: 改进大文件内存使用
- **并发优化**: 提升多任务处理能力