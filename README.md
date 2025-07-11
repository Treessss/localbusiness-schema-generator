# 本地商家信息提取器

一个基于 FastAPI 的本地商家信息爬虫服务，支持从google map提取商家详细信息，包括评分、地址、电话、营业时间等数据。

## 功能特性

- 🚀 高性能异步爬虫引擎
- 📊 实时数据提取和缓存
- 🔄 智能重试和错误处理
- 📈 内置监控和统计面板
- 🐳 完整的容器化支持

## 部署方式

### 方式一：直接部署

#### 环境要求
- Python 3.9+
- Redis 服务器
- Chrome/Chromium 浏览器

#### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/Treessss/localbusiness-schema-generator.git
   cd localbusiness
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置 Redis 连接等参数
   ```

4. **启动 Redis 服务**
   ```bash
   # macOS
   brew services start redis
   
   # Ubuntu/Debian
   sudo systemctl start redis-server
   ```

5. **运行应用**
   ```bash
   python start_with_monitor.py
   ```

6. **访问服务**
   - 爬取页面: http://localhost:8000
   - 监控面板: http://localhost:8001


### 方式二：Docker Compose 部署（推荐）

#### 前置要求
- Docker Engine
- Docker Compose

#### 部署步骤

1. **一键启动**
   ```bash
   docker-compose up -d
   ```

2. **查看服务状态**
   ```bash
   docker-compose ps
   ```

3. **查看日志**
   ```bash
   # 查看所有服务日志
   docker compose logs -f
   
   # 查看特定服务日志
   docker compose logs -f web
   docker compose logs -f redis
   ```

4. **停止服务**
   ```bash
   docker compose down
   ```

5. **重新构建**
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

#### 服务配置

- **Web 服务**: 端口 8000，配置 8核16G 资源限制
- **Redis 服务**: 端口 6380，数据持久化存储
- **数据卷**: `redis_data` 用于 Redis 数据持久化


## 监控和维护

- **健康检查**: `GET /health`
- **统计面板**: `http://localhost:8001`
- **API 文档**: `http://localhost:8000/docs`
- **日志文件**: `./logs/app.log`

## 故障排除

### 常见问题

1. **日志权限错误**
   ```bash
   mkdir -p logs
   chmod 755 logs/
   ```

2. **Redis 连接失败**
   - 检查 Redis 服务是否启动
   - 验证连接配置是否正确

3. **浏览器启动失败**
   - 确保系统已安装 Chrome/Chromium
   - 检查容器内浏览器权限

### 性能优化

- 调整并发限制: 修改 `CONCURRENCY_LIMIT` 环境变量
- 缓存配置: 调整 Redis 缓存过期时间
- 资源限制: 根据需要调整 Docker 资源配置
