# Docker 自动构建说明

## 功能

当代码推送到 `main` 或 `master` 分支时，GitHub Actions 会自动：
1. 构建 Docker 镜像
2. 推送到 Docker Hub (thesmallhancat/flow2api)

## 设置步骤

### 1. 在 GitHub 仓库中配置 Secrets

需要在 GitHub 仓库的 Settings > Secrets and variables > Actions 中添加以下 secrets：

- `DOCKER_USERNAME`: 你的 Docker Hub 用户名
- `DOCKER_PASSWORD`: 你的 Docker Hub 密码或访问令牌（推荐使用访问令牌）

### 2. 获取 Docker Hub 访问令牌（推荐）

1. 登录 [Docker Hub](https://hub.docker.com/)
2. 进入 Account Settings > Security
3. 点击 "New Access Token"
4. 创建令牌并复制（只显示一次，请妥善保存）
5. 将令牌作为 `DOCKER_PASSWORD` secret 添加到 GitHub

### 3. 工作流触发

- **Push 到 main/master 分支**: 自动构建并推送镜像
- **创建 Tag (v*格式)**: 构建并推送带版本标签的镜像
- **Pull Request**: 仅构建镜像（不推送），用于验证

### 4. 镜像标签

- `latest`: main/master 分支的最新版本
- `main`: main 分支的镜像
- `v1.0.0`: 语义化版本标签（如果创建了对应的 git tag）
- `v1.0`, `v1`: 版本别名

## 使用

推送代码后，可以在以下位置查看构建状态：
- GitHub Actions 页面: `https://github.com/raomaiping/flow2api/actions`
- Docker Hub: `https://hub.docker.com/r/thesmallhancat/flow2api`

构建完成后，可以使用以下命令拉取镜像：

```bash
docker pull thesmallhancat/flow2api:latest
```

或使用 docker-compose：

```bash
docker-compose pull
docker-compose up -d
```

