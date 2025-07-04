# Redis缓存配置指南

本项目已支持Redis缓存，可以将数据从内存缓存迁移到Redis中，提供更好的性能和持久化能力。

## 功能特性

- **自动回退**: 如果Redis不可用，系统会自动回退到内存缓存
- **异步操作**: 所有缓存操作都是异步的，不会阻塞主线程
- **连接池**: 使用连接池管理Redis连接，提高性能
- **统计信息**: 提供详细的缓存统计信息
- **过期清理**: 自动清理过期的缓存条目

## 安装Redis

### macOS (使用Homebrew)
```bash
brew install redis
brew services start redis
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### CentOS/RHEL
```bash
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

### Docker
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

## 配置环境变量

1. 复制环境变量示例文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置Redis连接参数：
```bash
# 缓存配置
USE_REDIS=true

# Redis连接配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Redis连接池配置
REDIS_MAX_CONNECTIONS=10
REDIS_RETRY_ON_TIMEOUT=true
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

# 缓存配置
CACHE_TTL=3600
CACHE_CLEANUP_INTERVAL=300
```

## 测试Redis缓存

运行测试脚本验证Redis缓存功能：

```bash
python test_redis_cache.py
```

如果Redis配置正确，你应该看到类似以下的输出：
```
开始测试Redis缓存功能...
缓存类型: RedisCache

1. 测试设置缓存...
✓ 缓存设置成功

2. 测试获取缓存...
✓ 缓存获取成功: 测试商家

3. 测试缓存统计...
✓ 缓存统计: {...}

4. 测试清理过期缓存...
✓ 清理过期缓存: 0 个条目

5. 测试清除所有缓存...
✓ 清除所有缓存: 1 个条目

✓ 所有Redis缓存测试通过！
```

## 启动应用

确保Redis服务正在运行，然后启动应用：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

应用启动时会自动检测Redis可用性：
- 如果Redis可用，将使用Redis缓存
- 如果Redis不可用，将自动回退到内存缓存

## 监控缓存状态

### API端点

- `GET /api/cache/stats` - 获取缓存统计信息
- `DELETE /api/cache/all` - 清除所有缓存
- `DELETE /api/cache/expired` - 清理过期缓存
- `GET /api/health` - 健康检查（包含缓存信息）

### Redis CLI监控

```bash
# 连接到Redis
redis-cli

# 查看所有键
KEYS *

# 查看特定键的值
GET "cache:https://maps.app.goo.gl/..."

# 查看键的TTL
TTL "cache:https://maps.app.goo.gl/..."

# 查看Redis信息
INFO
```

## 故障排除

### Redis连接失败

1. 检查Redis服务是否运行：
```bash
redis-cli ping
```
应该返回 `PONG`

2. 检查Redis配置：
```bash
redis-cli CONFIG GET bind
redis-cli CONFIG GET port
```

3. 检查防火墙设置（如果Redis在远程服务器）

### 应用回退到内存缓存

检查应用日志，查找类似以下的警告信息：
```
WARNING: Redis requested but not available, using memory cache
ERROR: Failed to create Redis cache, falling back to memory cache: ...
```

### 性能问题

1. 调整Redis连接池大小：
```bash
REDIS_MAX_CONNECTIONS=20
```

2. 调整超时设置：
```bash
REDIS_SOCKET_CONNECT_TIMEOUT=10
REDIS_SOCKET_TIMEOUT=10
```

3. 监控Redis内存使用：
```bash
redis-cli INFO memory
```

## 生产环境建议

1. **持久化配置**: 启用Redis的RDB或AOF持久化
2. **内存限制**: 设置合适的maxmemory和淘汰策略
3. **监控**: 使用Redis监控工具（如RedisInsight）
4. **备份**: 定期备份Redis数据
5. **集群**: 对于高可用性，考虑使用Redis集群或哨兵模式

## 从内存缓存迁移

如果你之前使用的是内存缓存，切换到Redis后：

1. 现有的内存缓存数据会丢失（这是正常的）
2. 新的请求会自动缓存到Redis中
3. 应用重启后，Redis中的缓存数据会保留

这就完成了从内存缓存到Redis缓存的迁移！