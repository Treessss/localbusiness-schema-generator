# 本地商家信息提取器

一个基于 FastAPI 的 Web 应用程序，用于从 Google Maps 链接中提取本地商家信息并生成符合 Schema.org 标准的结构化数据。

## 功能特性

- 🔍 **智能信息提取**: 从 Google Maps 链接中自动提取商家详细信息
- 📊 **结构化数据生成**: 生成符合 Schema.org LocalBusiness 标准的 JSON-LD 格式数据
- ⏰ **智能营业时间处理**: 自动解析和格式化营业时间，支持 AM/PM 推断
- 🌐 **多语言支持**: 支持中英文商家信息处理
- 🚀 **高性能**: 基于异步处理，支持并发请求
- 📱 **现代化界面**: 响应式 Web 界面，支持移动设备

## 技术栈

- **后端框架**: FastAPI
- **网页抓取**: Playwright
- **数据解析**: BeautifulSoup4
- **数据验证**: Pydantic
- **前端**: HTML5 + CSS3 + JavaScript
- **部署**: Docker 支持

## 快速开始

### 环境要求

- Python 3.8+
- Node.js (用于 Playwright)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd localbusiness
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **安装 Playwright 浏览器**
   ```bash
   playwright install-deps
   playwright install chromium
   ```

4. **启动应用**
   
   **方式一：标准启动**
   ```bash
   python run.py
   ```
   
   **方式二：无头模式启动（推荐服务器环境）**
   ```bash
   python run_headless.py
   ```
   
   **方式三：完整服务启动（包含监控）**
   ```bash
   python start_with_monitor.py
   ```

5. **访问应用**
   打开浏览器访问: http://localhost:8000

## 使用方法

### Web 界面

1. 在首页输入 Google Maps 商家链接
2. 点击"提取信息"按钮
3. 查看提取的商家信息和生成的结构化数据

### API 接口

**提取商家信息**
```bash
POST /api/extract
Content-Type: application/json

{
  "url": "https://maps.google.com/..."
}
```

**响应示例**
```json
{
  "success": true,
  "data": {
    "name": "商家名称",
    "rating": 4.5,
    "review_count": 123,
    "address": {
      "street": "街道地址",
      "city": "城市",
      "state": "省份",
      "postal_code": "邮编",
      "country": "国家"
    },
    "phone": "+1234567890",
    "website": "https://example.com",
    "opening_hours": [
      {
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": "Monday",
        "opens": "09:00",
        "closes": "17:00"
      }
    ],
    "business_type": "餐厅",
    "price_range": "$$",
    "images": ["image_url1", "image_url2"]
  },
  "schema": {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "商家名称",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "街道地址",
      "addressLocality": "城市",
      "addressRegion": "省份",
      "postalCode": "邮编",
      "addressCountry": "国家"
    },
    "telephone": "+1234567890",
    "url": "https://example.com",
    "openingHoursSpecification": [...],
    "aggregateRating": {
      "@type": "AggregateRating",
      "ratingValue": 4.5,
      "reviewCount": 123
    }
  }
}
```

## 项目结构

```
localbusiness/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── crawler.py           # 网页爬虫核心逻辑
│   ├── models.py            # 数据模型定义
│   ├── schema_generator.py  # Schema.org 数据生成器
│   ├── cache.py             # 缓存管理
│   ├── middleware.py        # 中间件
│   ├── stats.py             # 统计功能
│   └── utils.py             # 工具函数
├── static/
│   ├── index.html          # 前端页面
│   ├── monitor.html        # 监控页面
│   └── stats.html          # 统计页面
├── tests/                  # 测试文件
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api_extract.py
│   └── test_response_format.py
├── run.py                  # 标准启动脚本
├── run_headless.py         # 无头模式启动脚本
├── start_with_monitor.py   # 完整服务启动脚本
├── fix_playwright_deps.py  # Playwright依赖修复脚本
├── monitor.py              # 监控服务
├── requirements.txt        # Python 依赖
├── docker-compose.yml      # Docker Compose 配置
├── Dockerfile             # Docker 配置
├── README.md              # 项目说明
├── MONITOR_README.md       # 监控功能说明
├── REDIS_SETUP.md          # Redis 配置说明
└── TESTING.md              # 测试说明
```

## 核心功能

### 商家信息提取

- **基本信息**: 商家名称、评分、评论数量
- **联系信息**: 地址、电话、网站
- **营业信息**: 营业时间、价格范围、商家类型
- **媒体内容**: 商家图片

### 营业时间智能处理

- 自动识别 AM/PM 格式
- 智能推断缺失的 AM/PM 标识
- 支持多种时间格式
- 合并相同时间段的日期

### Schema.org 结构化数据

- 符合 LocalBusiness 标准
- JSON-LD 格式输出
- 支持搜索引擎优化
- 完整的地址和联系信息结构

## 配置选项

### 环境变量

- `LOG_LEVEL`: 日志级别 (默认: INFO)
- `MAX_CONCURRENT_REQUESTS`: 最大并发请求数 (默认: 10)
- `REQUEST_TIMEOUT`: 请求超时时间 (默认: 30秒)

### 爬虫配置

```python
# 在 crawler.py 中可以调整的参数
PAGE_LOAD_TIMEOUT = 30000  # 页面加载超时
WAIT_FOR_CONTENT = 3000    # 等待内容加载时间
USER_AGENT = "..."         # 自定义 User Agent
```

## 部署

### Docker 部署（推荐）

**方式一：使用 Docker Compose（推荐）**
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

**方式二：手动构建**
```bash
# 构建镜像
docker build -t localbusiness .

# 运行容器
docker run -p 8000:8000 localbusiness
```

### 本地部署

**标准启动**
```bash
python run.py
```

**无头模式启动（服务器环境推荐）**
```bash
python run_headless.py --host 0.0.0.0 --port 8000
```

**完整服务启动（包含监控）**
```bash
python start_with_monitor.py
```

### 生产环境部署

```bash
# 使用 Gunicorn 部署
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用无头模式脚本
python run_headless.py --host 0.0.0.0 --port 8000
```

### 依赖问题快速解决

如果遇到 Playwright 依赖问题：

```bash
# 运行自动修复脚本
python fix_playwright_deps.py

# 或直接使用 Docker（推荐）
docker-compose up -d
```

## 开发指南

### 添加新的提取字段

1. 在 `models.py` 中添加新的字段定义
2. 在 `crawler.py` 中实现提取逻辑
3. 在 `schema_generator.py` 中添加 Schema.org 映射

### 自定义营业时间解析

在 `crawler.py` 的 `_format_opening_hours` 方法中添加新的时间格式支持。

## 故障排除

### 常见问题

1. **Playwright 依赖缺失错误**
   
   **错误信息**: `Host system is missing dependencies to run browsers`
   
   **解决方案**:
   
   **方案一：自动修复（推荐）**
   ```bash
   python fix_playwright_deps.py
   ```
   
   **方案二：手动安装**
   ```bash
   # 安装系统依赖
   playwright install-deps
   
   # 安装浏览器
   playwright install chromium
   
   # 对于Ubuntu/Debian系统
   sudo apt-get update
   sudo apt-get install -y libatk-bridge2.0-0 libatspi2.0-0 libgbm1
   
   # 对于CentOS/RHEL系统
   sudo yum install -y atk at-spi2-atk mesa-libgbm
   ```
   
   **方案三：Docker部署（强烈推荐）**
   ```bash
   docker-compose up -d
   ```

2. **Playwright 安装失败**
   ```bash
   # 升级pip和setuptools
   pip install --upgrade pip setuptools wheel
   
   # 重新安装Playwright
   pip install --upgrade playwright
   playwright install chromium
   ```

3. **页面加载超时**
   - 检查网络连接
   - 增加 `PAGE_LOAD_TIMEOUT` 值
   - 确认 Google Maps 链接有效
   - 尝试无头模式启动: `python run_headless.py`

4. **信息提取不完整**
   - 检查页面结构是否发生变化
   - 查看日志获取详细错误信息
   - 尝试不同的 Google Maps 链接格式

5. **服务器环境部署问题**
   - 使用无头模式: `python run_headless.py`
   - 检查系统架构兼容性
   - 考虑使用Docker部署
   - 确保有足够的系统资源

### 日志调试

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 更新日志

### v1.0.0
- 初始版本发布
- 基本商家信息提取功能
- Schema.org 结构化数据生成
- Web 界面和 API 接口

### v1.1.0
- 增强营业时间解析
- 添加 AM/PM 智能推断
- 优化错误处理
- 改进用户界面

## 联系方式

如有问题或建议，请通过以下方式联系：

- 创建 Issue
- 发送邮件至: [your-email@example.com]
- 项目主页: [project-homepage]