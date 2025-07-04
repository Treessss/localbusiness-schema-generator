# API监控系统使用指南

本项目现在支持独立的API监控功能，可以在不同端口运行监控服务，实时查看API统计数据。

## 🚀 快速开始

### 方式一：使用便捷启动脚本（推荐）

```bash
# 同时启动API服务器和监控服务器
python start_with_monitor.py

# 自定义端口
python start_with_monitor.py --api-port 8000 --monitor-port 8001

# 只启动API服务器
python start_with_monitor.py --no-monitor

# 只启动监控服务器（需要API服务器已在运行）
python start_with_monitor.py --monitor-only
```

### 方式二：分别启动服务

```bash
# 1. 启动主API服务器
python run.py --port 8000

# 2. 在另一个终端启动监控服务器
python monitor.py --port 8001 --api-port 8000
```

## 📊 访问监控界面

启动成功后，可以通过以下地址访问：

- **主API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **内置统计页面**: http://localhost:8000/stats
- **独立监控中心**: http://localhost:8001

## 🔧 配置选项

### 主API服务器 (run.py)

```bash
python run.py [选项]

选项:
  --port PORT     服务器端口 (默认: 8000)
  --host HOST     服务器主机 (默认: 0.0.0.0)
```

### 独立监控服务器 (monitor.py)

```bash
python monitor.py [选项]

选项:
  --port PORT         监控服务器端口 (默认: 8001)
  --host HOST         监控服务器主机 (默认: 0.0.0.0)
  --api-host HOST     API服务器主机 (默认: localhost)
  --api-port PORT     API服务器端口 (默认: 8000)
```

### 便捷启动脚本 (start_with_monitor.py)

```bash
python start_with_monitor.py [选项]

选项:
  --api-port PORT       API服务器端口 (默认: 8000)
  --api-host HOST       API服务器主机 (默认: 0.0.0.0)
  --monitor-port PORT   监控服务器端口 (默认: 8001)
  --monitor-host HOST   监控服务器主机 (默认: 0.0.0.0)
  --no-monitor          只启动API服务器
  --monitor-only        只启动监控服务器
```

## 📈 监控功能特性

### 实时统计指标

- **总请求数**: 累计API请求总数
- **成功请求数**: HTTP状态码2xx的请求数
- **失败请求数**: HTTP状态码4xx/5xx的请求数
- **成功率**: 成功请求占总请求的百分比

### 可视化图表

- **请求时间线**: 显示总请求、成功请求、失败请求的时间趋势
- **成功率趋势**: 显示API成功率的变化趋势
- **端点统计表**: 显示各个API端点的详细统计信息

### 实时更新

- 通过WebSocket实现实时数据推送
- 每2秒自动更新一次数据
- 自动重连机制，确保连接稳定性

## 🔗 API端点

### 统计相关API

- `GET /api/stats` - 获取完整统计数据
- `GET /api/stats/current` - 获取当前统计指标
- `GET /api/stats/timeline` - 获取时间线数据
- `GET /api/stats/endpoints` - 获取端点统计
- `WebSocket /ws/stats` - 实时统计数据推送

### 监控服务器API

- `GET /` - 监控主页
- `GET /api/stats` - 代理获取API统计数据
- `GET /api/health` - 监控服务器健康检查
- `WebSocket /ws/monitor` - 监控数据推送

## 🛠️ 使用场景

### 场景1：开发环境监控

```bash
# 启动开发环境，同时开启监控
python start_with_monitor.py
```

### 场景2：生产环境监控

```bash
# API服务器运行在8000端口
python run.py --port 8000

# 监控服务器运行在8001端口
python monitor.py --port 8001 --api-port 8000
```

### 场景3：远程监控

```bash
# 监控远程API服务器
python monitor.py --port 8001 --api-host remote-server.com --api-port 8000
```

### 场景4：多端口部署

```bash
# API服务器在9000端口
python run.py --port 9000

# 监控服务器在9001端口
python monitor.py --port 9001 --api-port 9000
```

## 🔍 故障排除

### 监控服务器无法连接API服务器

1. 检查API服务器是否正在运行
2. 确认端口号和主机地址是否正确
3. 检查防火墙设置
4. 查看监控服务器日志

### WebSocket连接失败

1. 检查浏览器是否支持WebSocket
2. 确认监控服务器正在运行
3. 检查网络连接
4. 尝试刷新页面

### 数据不更新

1. 检查API服务器是否有新的请求
2. 确认WebSocket连接状态
3. 查看浏览器控制台错误信息
4. 尝试重新连接

## 📝 注意事项

1. **端口冲突**: 确保选择的端口没有被其他服务占用
2. **资源消耗**: 监控服务会消耗一定的系统资源
3. **数据保留**: 统计数据仅在内存中保存，重启后会清空
4. **网络延迟**: 远程监控可能存在网络延迟
5. **浏览器兼容性**: 建议使用现代浏览器以获得最佳体验

## 🎯 最佳实践

1. **开发环境**: 使用便捷启动脚本同时启动两个服务
2. **生产环境**: 分别部署API服务器和监控服务器
3. **监控多个API**: 可以启动多个监控服务器实例
4. **定期检查**: 定期查看监控数据，及时发现问题
5. **日志记录**: 结合日志系统进行更详细的问题分析

---

如有问题或建议，请查看项目文档或提交Issue。