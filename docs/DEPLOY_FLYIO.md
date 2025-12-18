# Fly.io 部署指南

## 准备工作

1. 安装 flyctl：
```bash
# macOS/Linux
curl -L https://fly.io/install.sh | sh

# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex
```

2. 登录 Fly.io：
```bash
fly auth login
```

## 部署步骤

1. 在项目根目录初始化 Fly.io 应用：
```bash
fly launch --dockerfile Dockerfile.recaptcha-service --name recaptcha-service
```

2. 配置内存（至少 512M，建议 1G）：
```bash
fly scale memory 1024
```

3. 配置环境变量：
```bash
fly secrets set PLAYWRIGHT_HEADLESS=true
fly secrets set RECAPTCHA_SERVICE_PORT=8001
```

4. 部署：
```bash
fly deploy
```

## 配置文件 (fly.toml)

```toml
app = "recaptcha-service"
primary_region = "iad"  # 选择离你最近的区域

[build]
  dockerfile = "Dockerfile.recaptcha-service"

[env]
  PLAYWRIGHT_HEADLESS = "true"
  RECAPTCHA_SERVICE_PORT = "8001"

[http_service]
  internal_port = 8001
  force_https = true
  auto_stop_machines = false  # 保持服务运行
  auto_start_machines = true
  min_machines_running = 1
  processes = ["app"]

[[vm]]
  memory_mb = 1024
```

## 查看日志

```bash
fly logs
```

## 查看状态

```bash
fly status
```

## 访问服务

部署完成后，Fly.io 会提供一个 URL，例如：
- `https://recaptcha-service.fly.dev`

## 注意事项

1. **内存限制**：免费计划只有 256M，需要升级到至少 512M（付费约 $1.94/月）
2. **自动休眠**：Fly.io 免费计划可能会休眠，建议使用 `auto_stop_machines = false`
3. **区域选择**：选择离你最近的区域以减少延迟

