# 使用轻量级 Python 镜像
FROM python:3.11-slim

EXPOSE 8081
EXPOSE 8080

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    REDIS_URL=redis://host.docker.internal:6379

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

# 拷贝 requirements 先安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 和浏览器（以root身份，安装到全局位置）
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium && \
    playwright install-deps chromium && \
    chmod -R 755 /ms-playwright

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制项目文件
COPY . .

# 创建日志目录并设置权限
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# 切换到非 root 用户运行应用
USER appuser

# 确保appuser也能访问Playwright浏览器
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright


# 健康检查（防止容器假启动）
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# 启动命令
CMD ["sh", "-c", "python start_with_monitor.py"]
