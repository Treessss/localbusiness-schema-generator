# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    REDIS_URL=redis://redis:6379

# Detect system architecture and install system dependencies
RUN dpkg --print-architecture > /tmp/arch.txt && \
    echo "Detected architecture: $(cat /tmp/arch.txt)" && \
    apt-get update && apt-get install -y \
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
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers with system detection
RUN echo "Installing Playwright for $(dpkg --print-architecture) architecture..." && \
    playwright install chromium && \
    playwright install-deps chromium && \
    echo "Playwright installation completed for $(dpkg --print-architecture)"

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# Wait for Redis and start application with monitor
CMD ["sh", "-c", "echo 'Waiting for Redis...' && until redis-cli -h redis ping; do echo 'Redis not ready, waiting...'; sleep 2; done && echo 'Redis is ready!' && python start_with_monitor.py --api-host 0.0.0.0 --api-port 8000 --monitor-host 0.0.0.0 --monitor-port 8001"]