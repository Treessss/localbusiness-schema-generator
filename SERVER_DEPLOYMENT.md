# 服务器部署指南

本指南专门针对在服务器环境中部署 Google 商家 Schema 生成器，特别是解决 Playwright 浏览器依赖问题。

## 快速部署

### 方案一：Docker 部署（强烈推荐）

这是最简单、最可靠的部署方式，无需处理系统依赖问题。

```bash
# 1. 克隆项目
git clone <repository-url>
cd localbusiness-schema-generator

# 2. 启动服务
docker-compose up -d

# 3. 查看状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f

# 5. 访问服务
# http://your-server-ip:8000
```

### 方案二：Python 环境部署

如果无法使用 Docker，可以按以下步骤部署：

```bash
# 1. 克隆项目
git clone <repository-url>
cd localbusiness-schema-generator

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装 Python 依赖
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. 运行依赖修复脚本
python fix_playwright_deps.py

# 5. 启动服务（无头模式）
python run_headless.py --host 0.0.0.0 --port 8000
```

## 常见问题解决

### 1. Playwright 依赖缺失

**错误信息**：
```
Host system is missing dependencies to run browsers
```

**解决方案**：

**自动修复（推荐）**：
```bash
python fix_playwright_deps.py
```

**手动修复**：
```bash
# Ubuntu/Debian 系统
sudo apt-get update
sudo apt-get install -y libatk-bridge2.0-0 libatspi2.0-0 libgbm1
playwright install-deps
playwright install chromium

# CentOS/RHEL 系统
sudo yum install -y atk at-spi2-atk mesa-libgbm
playwright install chromium
```

### 2. numpy 安装失败

**错误信息**：
```
AttributeError: module 'pkgutil' has no attribute 'ImpImporter'
```

**解决方案**：
```bash
# 升级构建工具
pip install --upgrade pip setuptools wheel

# 安装预编译版本
pip install --only-binary=all numpy

# 或指定版本
pip install "numpy>=1.21.0,<2.0.0"
```

### 3. 端口被占用

**检查端口占用**：
```bash
lsof -i :8000
# 或
netstat -tulpn | grep 8000
```

**使用其他端口**：
```bash
python run_headless.py --port 8001
```

### 4. 防火墙配置

**开放端口**：
```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8000

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

## 性能优化

### 1. 系统资源配置

**最低要求**：
- CPU: 1 核心
- 内存: 1GB
- 磁盘: 2GB

**推荐配置**：
- CPU: 2+ 核心
- 内存: 2GB+
- 磁盘: 5GB+

### 2. 并发配置

**修改并发数**：
```bash
# 在 .env 文件中设置
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=30
```

**使用 Gunicorn 部署**：
```bash
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  --keep-alive 2
```

### 3. 内存优化

**无头模式配置**：
```bash
# 使用更严格的无头模式
python run_headless.py --host 0.0.0.0 --port 8000
```

**浏览器参数优化**（已在代码中配置）：
- `--no-sandbox`
- `--disable-dev-shm-usage`
- `--disable-gpu`
- `--single-process`

## 监控和日志

### 1. 启用监控

```bash
# 启动完整服务（包含监控）
python start_with_monitor.py

# 访问监控页面
# http://your-server-ip:8000/monitor
```

### 2. 日志配置

**查看实时日志**：
```bash
# Docker 部署
docker-compose logs -f

# Python 部署
tail -f app.log
```

**调整日志级别**：
```bash
# 在 .env 文件中设置
LOG_LEVEL=DEBUG
```

### 3. 健康检查

**API 健康检查**：
```bash
curl http://localhost:8000/health
```

**服务状态检查**：
```bash
# 检查进程
ps aux | grep python

# 检查端口
netstat -tulpn | grep 8000
```

## 安全配置

### 1. 反向代理

**Nginx 配置示例**：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. HTTPS 配置

**使用 Let's Encrypt**：
```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

### 3. 访问限制

**IP 白名单**（在 Nginx 中配置）：
```nginx
location / {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    
    proxy_pass http://127.0.0.1:8000;
}
```

## 备份和恢复

### 1. 数据备份

```bash
# 备份配置文件
tar -czf backup-$(date +%Y%m%d).tar.gz \
  .env \
  docker-compose.yml \
  requirements.txt
```

### 2. 服务恢复

```bash
# 停止服务
docker-compose down
# 或
pkill -f "python.*run_headless"

# 恢复配置
tar -xzf backup-20231201.tar.gz

# 重启服务
docker-compose up -d
# 或
python run_headless.py --host 0.0.0.0 --port 8000 &
```

## 故障排除清单

### 部署前检查

- [ ] 系统要求满足（Python 3.8+）
- [ ] 网络连接正常
- [ ] 端口未被占用
- [ ] 有足够的磁盘空间
- [ ] 防火墙配置正确

### 部署后验证

- [ ] 服务正常启动
- [ ] API 接口响应正常
- [ ] 前端页面可访问
- [ ] 爬虫功能正常
- [ ] 日志记录正常

### 常用命令

```bash
# 检查服务状态
curl http://localhost:8000/health

# 测试 API
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://maps.google.com/..."}'

# 查看进程
ps aux | grep python

# 查看端口
netstat -tulpn | grep 8000

# 查看日志
tail -f app.log

# 重启服务
# Docker
docker-compose restart

# Python
pkill -f "python.*run_headless" && python run_headless.py &
```

## 联系支持

如果遇到无法解决的问题：

1. 查看项目 Issues
2. 运行诊断脚本：`python fix_playwright_deps.py`
3. 收集错误日志和系统信息
4. 考虑使用 Docker 部署方案

---

**推荐部署方案优先级**：
1. Docker Compose 部署
2. Python 无头模式部署
3. 标准 Python 部署

**生产环境建议**：
- 使用 Docker 部署
- 配置反向代理
- 启用 HTTPS
- 设置监控和日志
- 定期备份配置