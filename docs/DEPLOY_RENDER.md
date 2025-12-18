# Render 部署指南

## 准备工作

1. 访问 [Render.com](https://render.com) 注册账号
2. 连接 GitHub 账号（推荐）或使用 Git 部署

## 部署步骤

### 方式1: 通过 Web Dashboard（推荐）

1. **创建新 Web Service**
   - 登录 Render Dashboard
   - 点击 "New +" → "Web Service"
   - 连接 GitHub 仓库

2. **配置服务**
   - **Name**: `recaptcha-service`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile.recaptcha-service`
   - **Docker Context**: `.` (项目根目录)

3. **环境变量**
   ```
   PLAYWRIGHT_HEADLESS=true
   RECAPTCHA_SERVICE_PORT=8001
   ```

4. **资源配置**
   - **Plan**: Free
   - **Instance Type**: Free
   - **CPU**: 共享 CPU（约 0.5 vCPU）
   - **Memory**: 512M RAM
   - **Storage**: 1GB

5. **高级设置**
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: Yes (可选)

6. **部署**
   - 点击 "Create Web Service"
   - 等待构建和部署完成

### 方式2: 通过 Render Blueprint (render.yaml)

创建 `render.yaml`：

```yaml
services:
  - type: web
    name: recaptcha-service
    env: docker
    dockerfilePath: ./Dockerfile.recaptcha-service
    dockerContext: .
    plan: free
    healthCheckPath: /health
    envVars:
      - key: PLAYWRIGHT_HEADLESS
        value: true
      - key: RECAPTCHA_SERVICE_PORT
        value: 8001
```

然后在 Render Dashboard 中导入 Blueprint。

## 访问服务

部署完成后，Render 会提供一个 URL，例如：
- `https://recaptcha-service.onrender.com`

## 资源配置详情

Render 免费计划规格：
- **CPU**: 共享 CPU（约 0.5 vCPU）
- **Memory**: 512M RAM
- **Storage**: 1GB
- **Bandwidth**: 100GB/月
- **Runtime**: 750 小时/月

## 注意事项

1. **休眠机制**：免费计划在 15 分钟无活动后会休眠，首次请求会慢一些（约 30 秒唤醒）
2. **内存限制**：免费计划限制 512M RAM，刚好够用（reCAPTCHA 服务最低要求）
3. **CPU 限制**：共享 CPU（约 0.5 vCPU），对于 Playwright 来说足够，但可能比专用 CPU 稍慢
4. **带宽限制**：免费计划有带宽限制（100GB/月），但一般足够使用
5. **保持活跃**：可以使用外部监控服务定期 ping 来防止休眠（可选）

## 防止休眠（可选）

使用 [UptimeRobot](https://uptimerobot.com) 或类似服务：
- 每 5 分钟访问一次 `/health` 端点
- 这样服务就不会休眠

