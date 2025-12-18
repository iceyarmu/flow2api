# 自实现 reCAPTCHA 方案测试结果

## 测试日期
2025-12-17

## 测试环境
- Python 3.11
- Playwright 1.56.0
- Chromium 浏览器（已安装）
- Windows 10

## 测试结果

### ✅ 测试成功

**测试脚本**: `test_self_recaptcha.py`

**结果**: 
- ✅ 成功获取 reCAPTCHA v3 token
- ✅ Token 长度: 1785 字符
- ✅ Token 格式正确（Base64 编码字符串）

**关键改进**:
1. **自动检测并注入 reCAPTCHA v3 脚本**
   - 检查页面是否已加载 reCAPTCHA v3
   - 如果未加载，自动注入 `https://www.google.com/recaptcha/api.js?render=<site_key>`
   - 等待脚本加载和初始化

2. **改进的等待机制**
   - 轮询检查 `window.grecaptcha.execute` 是否可用
   - 最多等待20秒（每0.5秒检查一次）
   - 确保 reCAPTCHA 完全初始化后再执行

3. **更好的错误处理**
   - 检查 `window.grecaptcha` 是否存在
   - 检查 `execute` 方法是否可用
   - 提供详细的错误信息

## 实现原理

### 工作流程
1. 使用 Playwright 启动浏览器（本地测试使用有头模式，Docker 中使用无头模式）
2. 访问目标页面: `https://labs.google/fx/tools/flow/project/{project_id}`
3. 检查页面是否已加载 reCAPTCHA v3 脚本
4. 如果未加载，注入 reCAPTCHA v3 脚本: `https://www.google.com/recaptcha/api.js?render={site_key}`
5. 等待 `window.grecaptcha.execute` 方法可用
6. 调用 `grecaptcha.execute(site_key, {action: 'FLOW_GENERATION'})` 获取 token
7. 返回 token

### 关键代码
```python
# 检查并注入 reCAPTCHA v3 脚本
script_loaded = await page.evaluate(f"""
    () => {{
        if (window.grecaptcha && typeof window.grecaptcha.execute === 'function') {{
            return true;
        }}
        return false;
    }}
""")

if not script_loaded:
    await page.evaluate(f"""
        () => {{
            return new Promise((resolve) => {{
                const script = document.createElement('script');
                script.src = 'https://www.google.com/recaptcha/api.js?render={website_key}';
                script.async = true;
                script.defer = true;
                script.onload = () => resolve(true);
                script.onerror = () => resolve(false);
                document.head.appendChild(script);
            }});
        }}
    """)

# 执行 reCAPTCHA v3
token = await window.grecaptcha.execute(websiteKey, {
    action: 'FLOW_GENERATION'
})
```

## 性能指标

- **浏览器启动时间**: ~2-3 秒
- **页面加载时间**: ~2-5 秒（取决于网络）
- **reCAPTCHA 脚本加载**: ~1-3 秒
- **Token 获取时间**: ~0.5-1 秒
- **总耗时**: ~5-12 秒

## 注意事项

### ⚠️ 局限性

1. **性能开销**
   - 每次获取 token 都需要启动浏览器（如果未复用）
   - 占用内存较大（~500MB-1GB）
   - 比 yescaptcha 方案慢（yescaptcha 通常 3-10 秒，自实现 5-12 秒）

2. **资源消耗**
   - 需要安装 Playwright 和 Chromium（增加 ~500-900MB 镜像大小）
   - 需要更多内存和 CPU 资源

3. **维护成本**
   - 需要处理浏览器兼容性问题
   - 如果 Google 更新 reCAPTCHA 机制，可能需要调整代码
   - 可能需要处理反自动化检测（目前未遇到，但可能在未来需要）

4. **页面要求**
   - 理论上需要访问目标页面，但实际上可以注入脚本来获取 token
   - 某些页面可能需要登录，但 reCAPTCHA v3 可以在未登录状态下工作

### ✅ 优势

1. **完全免费**
   - 不需要第三方服务费用
   - 只需服务器资源成本

2. **完全自主控制**
   - 不依赖第三方平台
   - 可以自定义实现逻辑

3. **隐私保护**
   - 数据不经过第三方服务
   - 所有操作在本地完成

## 使用建议

### 推荐场景
- 开发/测试环境
- 低频率请求（每小时 < 100 次）
- 对成本敏感的场景
- 对隐私要求高的场景

### 不推荐场景
- 生产环境（高并发）
- 对性能要求高的场景
- 资源受限的环境（内存 < 2GB）

### 混合方案（推荐）
- 默认使用 yescaptcha（稳定、快速）
- 在 yescaptcha 失败时回退到自实现方案
- 在配置中可以选择使用哪种方案

## 部署建议

### Docker 部署
参考 `Dockerfile.playwright` 和 `DOCKER_DEPLOYMENT_PLAYWRIGHT.md`

### 配置
在 `config/setting.toml` 中启用：
```toml
[recaptcha]
use_self = true  # 启用自实现方案（优先使用，失败时回退到 yescaptcha）
```

### 内存要求
- 建议至少 2GB 可用内存
- Docker 中需要设置 `--shm-size=2gb`

## 测试命令

```bash
# 基础测试
python test_self_recaptcha.py

# 详细测试（带调试信息）
python test_self_recaptcha_detailed.py

# 指定 project_id
python test_self_recaptcha.py <project_id>
```

## 结论

✅ **自实现的 reCAPTCHA 方案是可行的**，可以在本地成功获取 token。

但是，考虑到性能、资源消耗和维护成本，**建议在生产环境中优先使用 yescaptcha，自实现方案作为备用**。

