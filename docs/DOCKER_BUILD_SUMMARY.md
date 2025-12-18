# Docker 镜像构建说明

## 当前配置

项目配置了两个独立的 Docker 镜像构建流程：

### 1. 主应用镜像 (flow2api)

**Workflow**: `.github/workflows/docker-build.yml`

**触发条件**:
- 推送到 main/master 分支
- 修改以下文件时触发：
  - `src/**` - 源代码
  - `main.py` - 主程序入口
  - `Dockerfile` - 主应用Dockerfile
  - `requirements.txt` - 主应用依赖
  - `config/**` - 配置文件
  - `static/**` - 静态文件
- **排除**: reCAPTCHA服务相关文件

**构建**:
- Dockerfile: `Dockerfile`
- 镜像: `ghcr.io/YOUR_USERNAME/flow2api:latest`
- Registry: GitHub Container Registry (ghcr.io)

### 2. reCAPTCHA Token Service 镜像

**Workflow**: `.github/workflows/recaptcha-service-deploy.yml`

**触发条件**:
- 推送到 main/master 分支
- 修改以下文件时触发：
  - `recaptcha_service.py`
  - `Dockerfile.recaptcha-service`
  - `src/services/self_recaptcha_solver.py`
  - `.github/workflows/recaptcha-service-deploy.yml`

**构建**:
- Dockerfile: `Dockerfile.recaptcha-service`
- 镜像: `ghcr.io/YOUR_USERNAME/flow2api/flow2api-recaptcha-service:latest`
- Registry: GitHub Container Registry (ghcr.io)

## 构建场景

### 场景1: 只修改主应用代码
- **触发**: 主应用 workflow
- **构建**: 1个镜像（主应用）
- **结果**: `ghcr.io/YOUR_USERNAME/flow2api:latest`

### 场景2: 只修改reCAPTCHA服务代码
- **触发**: reCAPTCHA服务 workflow
- **构建**: 1个镜像（reCAPTCHA服务）
- **结果**: `ghcr.io/YOUR_USERNAME/flow2api/flow2api-recaptcha-service:latest`

### 场景3: 同时修改两种代码
- **触发**: 两个 workflow 都触发
- **构建**: 2个镜像
- **结果**: 
  - `ghcr.io/YOUR_USERNAME/flow2api:latest`
  - `ghcr.io/YOUR_USERNAME/flow2api/flow2api-recaptcha-service:latest`

### 场景4: 创建版本标签 (v*)
- **触发**: 主应用 workflow（标签触发）
- **构建**: 1个镜像（主应用）
- **结果**: `ghcr.io/YOUR_USERNAME/flow2api:v1.0.0` 等

## 优势

✅ **智能触发**: 使用 paths 过滤，只构建相关的镜像
✅ **节省资源**: 避免不必要的构建
✅ **独立部署**: 两个服务可以独立部署和更新
✅ **统一Registry**: 都使用 ghcr.io，无需配置 Docker Hub credentials

## 使用镜像

### 主应用
```bash
docker pull ghcr.io/YOUR_USERNAME/flow2api:latest
```

### reCAPTCHA Token Service
```bash
docker pull ghcr.io/YOUR_USERNAME/flow2api/flow2api-recaptcha-service:latest
```

## 注意事项

1. **镜像命名**: 
   - 主应用: `ghcr.io/YOUR_USERNAME/flow2api`
   - 服务: `ghcr.io/YOUR_USERNAME/flow2api/flow2api-recaptcha-service`
   - 注意服务镜像有额外的 `/flow2api-recaptcha-service` 路径

2. **构建时间**: 
   - 主应用: ~5-10分钟
   - reCAPTCHA服务: ~10-15分钟（包含Playwright和Chromium）

3. **并发构建**: 如果同时触发两个构建，GitHub Actions会并行执行

