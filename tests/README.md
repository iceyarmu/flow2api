# 测试文件说明

本目录包含项目的所有测试脚本和测试结果文档。

## 📁 目录结构

```
tests/
├── README.md                           # 本文件
├── test_all_apis.py                    # 测试所有API端点
├── test_image_generation.py            # 测试图片生成API
├── test_recaptcha_service.py           # 测试reCAPTCHA Token Service
├── test_self_recaptcha.py              # 测试自实现reCAPTCHA（基础）
├── test_self_recaptcha_detailed.py     # 测试自实现reCAPTCHA（详细）
├── test_token_validity.py              # 测试生成的token有效性
└── results/                            # 测试结果文档
    ├── RECAPTCHA_SERVICE_TEST_RESULTS.md
    ├── SELF_RECAPTCHA_TEST_RESULTS.md
    └── TOKEN_VALIDITY_TEST_RESULTS.md
```

## 🧪 测试文件说明

### 1. test_all_apis.py
**功能**: 测试所有API端点的基本功能

**使用方法**:
```bash
python tests/test_all_apis.py
```

**测试内容**:
- 健康检查
- Token管理API
- 配置API
- 图片生成API（基础测试）

### 2. test_image_generation.py
**功能**: 详细测试图片生成API，查看返回参数

**使用方法**:
```bash
python tests/test_image_generation.py
```

**测试内容**:
- 流式响应解析
- 图片URL提取
- 响应格式验证

### 3. test_recaptcha_service.py
**功能**: 测试reCAPTCHA Token Service的API

**使用方法**:
```bash
# 首先启动服务
python recaptcha_service.py

# 在另一个终端运行测试
python tests/test_recaptcha_service.py

# 或指定project_id
python tests/test_recaptcha_service.py <project_id>
```

**测试内容**:
- 健康检查
- Token获取
- 并发请求测试

### 4. test_self_recaptcha.py
**功能**: 测试自实现的reCAPTCHA方案（基础版本）

**使用方法**:
```bash
python tests/test_self_recaptcha.py

# 或指定project_id
python tests/test_self_recaptcha.py <project_id>
```

**前置条件**:
- 需要安装 Playwright: `pip install playwright && playwright install chromium`
- 需要数据库中有有效的token和project_id

**测试内容**:
- 浏览器启动
- reCAPTCHA token获取
- Token格式验证

### 5. test_self_recaptcha_detailed.py
**功能**: 详细测试自实现的reCAPTCHA方案（带调试信息）

**使用方法**:
```bash
python tests/test_self_recaptcha_detailed.py

# 或指定project_id
python tests/test_self_recaptcha_detailed.py <project_id>
```

**测试内容**:
- 浏览器初始化过程
- 页面加载检查
- reCAPTCHA脚本加载
- 详细的错误信息

### 6. test_token_validity.py
**功能**: 测试生成的reCAPTCHA token是否有效

**使用方法**:
```bash
# 确保reCAPTCHA Token Service正在运行
python recaptcha_service.py

# 在另一个终端运行测试
python tests/test_token_validity.py

# 或指定project_id
python tests/test_token_validity.py <project_id>
```

**测试内容**:
- 从服务获取token
- Token格式分析
- 使用token调用Flow API验证有效性
- 图片生成验证

## 📊 测试结果文档

测试结果文档位于 `tests/results/` 目录：

- **RECAPTCHA_SERVICE_TEST_RESULTS.md** - reCAPTCHA Token Service的测试结果
- **SELF_RECAPTCHA_TEST_RESULTS.md** - 自实现reCAPTCHA方案的测试结果
- **TOKEN_VALIDITY_TEST_RESULTS.md** - Token有效性验证结果

## 🔧 运行所有测试

### 快速测试流程

1. **测试API端点**:
   ```bash
   python tests/test_all_apis.py
   ```

2. **测试图片生成**:
   ```bash
   python tests/test_image_generation.py
   ```

3. **测试reCAPTCHA服务**（需要先启动服务）:
   ```bash
   # 终端1: 启动服务
   python recaptcha_service.py
   
   # 终端2: 运行测试
   python tests/test_recaptcha_service.py
   python tests/test_token_validity.py
   ```

4. **测试自实现reCAPTCHA**（可选，需要Playwright）:
   ```bash
   python tests/test_self_recaptcha.py
   ```

## ⚙️ 环境要求

### 基础测试
- Python 3.8+
- 项目依赖: `pip install -r requirements.txt`

### reCAPTCHA Service测试
- 需要启动 `recaptcha_service.py`
- 需要数据库中有有效的token和project_id

### 自实现reCAPTCHA测试
- Playwright: `pip install playwright && playwright install chromium`
- 需要数据库中有有效的token和project_id

## 📝 注意事项

1. **测试顺序**: 某些测试依赖其他服务运行，请按顺序执行
2. **数据库**: 大部分测试需要数据库中有有效的token
3. **网络**: 部分测试需要网络连接
4. **资源**: 自实现reCAPTCHA测试需要较多内存（~500MB-1GB）

## 🐛 故障排查

### 测试失败

1. **检查服务是否运行**:
   ```bash
   curl http://localhost:8000/health  # 主服务
   curl http://localhost:8001/health  # reCAPTCHA服务
   ```

2. **检查数据库**:
   ```bash
   # 确认data/flow.db存在
   ls data/flow.db
   ```

3. **检查依赖**:
   ```bash
   pip install -r requirements.txt
   ```

### 导入错误

如果遇到导入错误，确保从项目根目录运行测试：
```bash
# 正确
cd /path/to/flow2api
python tests/test_all_apis.py

# 错误
cd tests
python test_all_apis.py
```

## 📚 相关文档

- [reCAPTCHA Service文档](../docs/RECAPTCHA_SERVICE_README.md)
- [部署文档](../docs/RECAPTCHA_SERVICE_DEPLOY.md)

