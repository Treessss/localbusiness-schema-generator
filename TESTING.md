# 测试文档

本项目包含完整的单元测试模块，专门用于测试 `/api/extract` 接口的输出格式和功能正确性。

## 📁 测试结构

```
tests/
├── __init__.py                 # 测试模块初始化
├── conftest.py                # pytest 配置和 fixtures
├── test_api_extract.py        # API 接口功能测试
└── test_response_format.py    # 响应格式验证测试
```

## 🧪 测试内容

### 1. API 接口功能测试 (`test_api_extract.py`)

- ✅ **成功响应格式测试**: 验证正常提取商家信息时的响应结构
- ✅ **缓存响应格式测试**: 验证从缓存返回数据时的响应格式
- ✅ **错误响应格式测试**: 验证发生错误时的响应结构
- ✅ **无效URL测试**: 验证无效Google商家URL的错误处理
- ✅ **JSON-LD格式测试**: 验证生成的JSON-LD script标签格式
- ✅ **请求参数验证**: 验证输入参数的验证逻辑
- ✅ **自定义描述测试**: 验证带自定义描述的请求处理

### 2. 响应格式验证测试 (`test_response_format.py`)

- ✅ **JSON Schema 验证**: 使用严格的JSON Schema验证响应格式
- ✅ **数据类型检查**: 验证每个字段的数据类型正确性
- ✅ **时间戳格式验证**: 验证ISO格式时间戳的正确性
- ✅ **JSON-LD内容验证**: 验证JSON-LD结构符合schema.org标准
- ✅ **错误响应结构**: 验证各种错误情况的响应格式
- ✅ **中文编码测试**: 验证中文字符的正确编码处理

## 🚀 运行测试

### 方法一：使用测试脚本（推荐）

```bash
# 运行所有测试
python run_tests.py

# 运行特定测试文件
python run_tests.py --file test_api_extract.py

# 运行特定测试函数
python run_tests.py --func test_extract_success_response_format

# 显示帮助信息
python run_tests.py --help-tests
```

### 方法二：直接使用 pytest

```bash
# 安装测试依赖
pip install -r requirements.txt

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_api_extract.py -v

# 运行特定测试函数
pytest tests/test_api_extract.py::TestExtractAPI::test_extract_success_response_format -v

# 运行带标记的测试
pytest -m "api" -v

# 显示测试覆盖率
pytest tests/ --cov=app --cov-report=html
```

## 📋 测试依赖

测试模块需要以下依赖包：

```
pytest==7.4.3              # 测试框架
pytest-asyncio==0.21.1     # 异步测试支持
jsonschema==4.20.0         # JSON Schema 验证
httpx==0.25.2              # HTTP 客户端（测试用）
```

## 🔧 测试配置

### pytest.ini 配置

- 测试发现模式：`test_*.py` 和 `*_test.py`
- 异步测试支持：自动模式
- 输出格式：详细模式，彩色输出
- 日志配置：显示测试过程中的日志

### conftest.py Fixtures

- `client`: FastAPI 测试客户端
- `mock_crawler`: Mock 爬虫实例
- `mock_cache`: Mock 缓存实例
- `mock_schema_generator`: Mock schema 生成器
- `sample_business_data`: 示例商家数据
- `valid_google_business_url`: 有效的Google商家URL

## 📊 响应格式规范

### 成功响应格式

```json
{
  "success": true,
  "script": "<script type=\"application/ld+json\">\n{...}\n</script>",
  "cached": false,
  "extracted_at": "2024-01-01T12:00:00.000000"
}
```

### 错误响应格式

```json
{
  "success": false,
  "error": "错误描述信息",
  "extracted_at": "2024-01-01T12:00:00.000000"
}
```

### JSON-LD 内容格式

```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "商家名称",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "街道地址"
  }
}
```

## 🎯 测试策略

### 1. 单元测试
- 测试单个函数和方法的正确性
- 使用 Mock 隔离外部依赖
- 验证输入输出格式

### 2. 集成测试
- 测试完整的API请求流程
- 验证各组件之间的协作
- 测试真实的HTTP请求响应

### 3. 格式验证
- 使用JSON Schema严格验证响应格式
- 验证数据类型和结构
- 确保符合API规范

## 🐛 调试测试

### 查看详细输出

```bash
# 显示详细的测试输出
pytest tests/ -v -s

# 显示失败测试的详细信息
pytest tests/ --tb=long

# 只运行失败的测试
pytest tests/ --lf
```

### 调试特定测试

```bash
# 在测试中添加断点
import pdb; pdb.set_trace()

# 使用 pytest 的调试模式
pytest tests/test_api_extract.py::test_function_name --pdb
```

## 📈 持续集成

测试模块设计为可以轻松集成到CI/CD流程中：

```yaml
# GitHub Actions 示例
- name: Run tests
  run: |
    pip install -r requirements.txt
    python run_tests.py
```

## 🔍 测试最佳实践

1. **隔离性**: 每个测试独立运行，不依赖其他测试
2. **可重复性**: 测试结果应该是确定的和可重复的
3. **快速性**: 使用Mock避免真实的网络请求
4. **全面性**: 覆盖正常流程、边界情况和错误情况
5. **可读性**: 测试名称和代码清晰表达测试意图

## 📝 添加新测试

当需要添加新的测试时：

1. 在相应的测试文件中添加测试函数
2. 使用描述性的函数名（以`test_`开头）
3. 添加适当的文档字符串
4. 使用现有的fixtures或创建新的fixtures
5. 确保测试覆盖正常和异常情况

```python
def test_new_feature_response_format(self, client, mock_dependencies):
    """测试新功能的响应格式"""
    # 设置测试数据
    # 执行测试
    # 验证结果
    pass
```