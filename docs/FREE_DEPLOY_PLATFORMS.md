# 免费部署平台对比

针对 reCAPTCHA Token Service 的免费部署平台推荐和对比。

## 快速对比

| 平台 | 免费资源 | CPU | 内存限制 | 休眠机制 | 推荐度 | 说明 |
|------|---------|-----|---------|---------|--------|------|
| **Fly.io** | 3 共享 CPU + 256M | 共享 CPU（约 0.25-0.5 vCPU） | 需升级到 512M+ | 可配置不休眠 | ⭐⭐⭐⭐ | 性能好，但需付费升级内存 |
| **Render** | 750 小时/月 | 共享 CPU（约 0.5 vCPU） | 512M | 15 分钟无活动休眠 | ⭐⭐⭐⭐⭐ | **最推荐**，完全免费 |
| **Railway** | $5/月额度 | 512M | 可配置 | ⭐⭐⭐ | 免费额度有限 |
| **Koyeb** | 2 服务 × 512M | 512M | 无 | ⭐⭐⭐⭐ | 较新平台，免费额度充足 |
| **Coolify** | 自托管 | 无限制 | 无 | ⭐⭐⭐ | 需要自有服务器 |

## 详细推荐

### 🏆 Render（最推荐）

**为什么推荐**：
- ✅ 512M RAM 刚好满足需求（最低要求）
- ✅ 共享 CPU（约 0.5 vCPU），足够运行 Playwright
- ✅ 完全免费（750小时/月足够）
- ✅ 操作简单，支持 Docker
- ✅ 自动 HTTPS
- ✅ 配置简单

**缺点**：
- ⚠️ 15 分钟无活动会休眠（首次请求慢 30 秒）
- ⚠️ 可以用外部监控防止休眠

**适用场景**：个人项目、测试环境、低频使用

**部署文档**：查看 [DEPLOY_RENDER.md](DEPLOY_RENDER.md)

---

### ⚡ Fly.io（性能优先）

**为什么推荐**：
- ✅ 性能好，全球边缘节点
- ✅ 可配置不休眠
- ✅ 自动 HTTPS
- ✅ 强大的 CLI 工具

**缺点**：
- ⚠️ 免费计划只有 256M（不够用）
- ⚠️ 需要升级到 512M+（约 $1.94/月）

**适用场景**：需要高性能、不介意少量费用

**部署文档**：查看 [DEPLOY_FLYIO.md](DEPLOY_FLYIO.md)

---

### 🚀 Koyeb（新兴平台）

**为什么推荐**：
- ✅ 免费提供 512M RAM
- ✅ 全球边缘节点
- ✅ 无休眠机制
- ✅ 操作简单

**缺点**：
- ⚠️ 平台较新，社区相对较小
- ⚠️ 免费额度可能变化

**适用场景**：想要免费且不休眠的服务

**部署方式**：
1. 访问 [koyeb.com](https://koyeb.com)
2. 连接 GitHub 仓库
3. 选择 Docker 部署
4. 使用 `Dockerfile.recaptcha-service`

---

### 💰 Railway（试用推荐）

**为什么推荐**：
- ✅ $5/月免费额度
- ✅ 操作简单
- ✅ 支持 Docker

**缺点**：
- ⚠️ 免费额度有限
- ⚠️ 超过后需付费

**适用场景**：短期试用、开发测试

---

## 资源需求

reCAPTCHA Token Service 的资源需求：

- **最低要求**：
  - CPU: 0.5 vCPU（共享 CPU 也可以）
  - RAM: 512M（必须）
  - 存储: 1GB
  - 网络: 需要访问 Google 服务

- **推荐配置**：
  - CPU: 0.5-1 vCPU
  - RAM: 1G（更稳定）
  - 存储: 2GB
  - 网络: 稳定的互联网连接

## 选择建议

### 场景1: 完全免费
👉 **选择 Render**（虽然会休眠，但完全免费）

### 场景2: 性能优先（愿意少量付费）
👉 **选择 Fly.io**（升级到 1G RAM，约 $2/月）

### 场景3: 不想休眠（完全免费）
👉 **选择 Koyeb**（512M RAM，无休眠）

### 场景4: 自有服务器
👉 **选择 Coolify**（完全自控）

## 防止休眠（Render 适用）

如果使用 Render，可以使用以下方法防止休眠：

1. **UptimeRobot**（免费）
   - 每 5 分钟访问一次 `/health` 端点
   - 注册：https://uptimerobot.com

2. **cron-job.org**（免费）
   - 设置定时任务访问服务
   - 注册：https://cron-job.org

3. **GitHub Actions**（免费）
   - 创建定时任务定期 ping 服务
   - 示例：
   ```yaml
   # .github/workflows/keep-alive.yml
   name: Keep Alive
   on:
     schedule:
       - cron: '*/5 * * * *'  # 每 5 分钟
   jobs:
     ping:
       runs-on: ubuntu-latest
       steps:
         - name: Ping service
           run: curl https://your-service.onrender.com/health
   ```

## 部署检查清单

部署后检查：

- [ ] 服务健康检查：`curl https://your-service.com/health`
- [ ] Token 获取测试：使用 `tests/test_recaptcha_service.py` 测试
- [ ] 监控服务状态（可选）
- [ ] 配置主应用的 `recaptcha_service_url`

## 问题排查

### 服务启动失败
- 检查内存是否足够（至少 512M）
- 查看日志了解具体错误

### Token 获取超时
- 检查网络连接
- 确认 Playwright 和 Chromium 已正确安装
- 查看服务日志

### 服务休眠
- 使用监控服务定期访问
- 或升级到付费计划（Fly.io）

## 更多资源

- [Render 部署指南](DEPLOY_RENDER.md)
- [Fly.io 部署指南](DEPLOY_FLYIO.md)
- [服务文档](RECAPTCHA_SERVICE_README.md)
- [部署文档](RECAPTCHA_SERVICE_DEPLOY.md)

