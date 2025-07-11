# 使用轻量级 Python 镜像
FROM python:3.11-slim

EXPOSE 8081
EXPOSE 8080

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    REDIS_URL=redis://host.docker.internal:6379 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 安装系统依赖（需要root权限）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 拷贝 requirements 文件并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 和 Chromium 浏览器
RUN playwright install chromium && \
    playwright install-deps chromium && \
    chmod -R 755 /ms-playwright

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 拷贝项目代码（确保 logs 目录也包括在内）
COPY . .

RUN chmod -R 777 /app/logs

# ✅ 修复：在 COPY 后重新设置权限，确保日志目录可写
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/logs

# 切换到非 root 用户运行应用
USER appuser

# 健康检查（FastAPI 健康接口）
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# 启动命令
CMD ["python", "start_with_monitor.py"]
