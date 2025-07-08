"""Google商家Schema生成器的FastAPI应用程序

这个应用程序提供以下功能：
1. 从Google Maps商家页面提取商家信息
2. 生成符合Schema.org标准的结构化数据
3. 提供缓存机制以提高性能
4. 实时统计和监控功能
5. WebSocket支持实时数据推送
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .models import (
    ExtractRequest,
    HealthResponse,
    LocalBusinessSchema
)
from .crawler import GoogleBusinessCrawler
from .schema_generator import SchemaGenerator
from .cache import cache
from .utils import is_google_business_url
from .middleware import StatsMiddleware
from .stats import api_stats

# 配置日志系统
logger.remove()  # 移除默认处理器

# 配置控制台日志输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 配置文件日志输出
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)  # 确保日志目录存在
logger.add(
    log_dir / "app.log",
    rotation="1 day",      # 每天轮转一次
    retention="30 days",   # 保留30天的日志
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",         # 文件日志记录更详细的信息
    encoding="utf-8"       # 确保中文字符正确编码
)

# 创建FastAPI应用
app = FastAPI(
    title="Google商家Schema生成器",
    description="提取Google商家信息并生成Schema.org结构化数据",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加统计中间件
app.add_middleware(StatsMiddleware)

# 添加CORS中间件（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("静态文件目录已挂载")
else:
    logger.warning("静态文件目录不存在")

# 初始化核心组件
schema_generator = SchemaGenerator()  # Schema生成器
crawler = GoogleBusinessCrawler(headless=True)  # 无头浏览器爬虫


@app.on_event("startup")
async def startup_event():
    """应用启动事件
    
    初始化应用程序的核心组件，包括：
    - 启动缓存定时清理任务
    - 初始化全局浏览器实例
    - 记录启动状态信息
    """
    logger.info("启动Google商家Schema生成器")
    logger.info(f"缓存已初始化，TTL为{cache.default_ttl_hours}小时")
    # 启动缓存定时清理任务
    await cache.start_cleanup_task()
    # 启动全局浏览器实例
    await crawler.start()
    logger.info("全局浏览器实例已启动")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理工作
    
    优雅地关闭应用程序，包括：
    - 停止全局浏览器实例
    - 停止缓存定时清理任务
    - 关闭缓存连接（如果是Redis缓存）
    - 记录关闭状态信息
    
    Note:
        确保所有资源都被正确释放，避免内存泄漏
    """
    logger.info("应用正在关闭...")
    
    # 停止全局浏览器实例
    try:
        await crawler.stop()
        logger.info("全局浏览器实例已停止")
    except Exception as e:
        logger.error(f"停止浏览器实例时出错: {e}")
    
    # 停止缓存定时清理任务
    try:
        await cache.stop_cleanup_task()
    except Exception as e:
        logger.error(f"停止缓存清理任务时出错: {e}")
    
    # 关闭缓存连接（如果是Redis缓存）
    try:
        if hasattr(cache, 'close'):
            await cache.close()
            logger.info("缓存连接已关闭")
    except Exception as e:
        logger.error(f"关闭缓存连接时出错: {e}")
    
    logger.info("应用关闭完成")


@app.get("/")
async def root():
    """提供应用程序主页
    
    返回静态HTML主页文件，用于用户界面交互。
    提供商家信息提取和Schema生成的Web界面。
    
    Returns:
        FileResponse: 主页HTML文件
        
    Note:
        需要确保static/index.html文件存在
    """
    return FileResponse('static/index.html')


@app.post("/api/extract")
async def extract_business_info(request: ExtractRequest):
    """提取Google商家信息并生成Schema.org结构化数据
    
    从Google Maps商家页面提取详细信息，生成符合Schema.org标准的
    JSON-LD结构化数据脚本。支持缓存机制以提高性能。
    
    功能特性：
    - 自动验证Google Maps URL格式
    - 智能缓存机制，避免重复爬取
    - 支持自定义商家描述
    - 支持强制刷新缓存
    - 生成可直接嵌入HTML的JSON-LD脚本
    
    Args:
        request: 包含URL和提取选项的请求对象
        
    Returns:
        dict: 包含以下字段的响应：
            - success: 提取是否成功
            - script: JSON-LD脚本标签（成功时）
            - cached: 是否来自缓存
            - extracted_at: 提取时间戳
            - error: 错误信息（失败时）
        
    Raises:
        HTTPException: 当URL无效时抛出400错误
    """
    url = str(request.url)

    logger.info(f"收到URL提取请求: {url}")

    # 验证URL格式是否为有效的Google商家URL
    if not is_google_business_url(url):
        logger.warning(f"无效的Google商家URL: {url}")
        raise HTTPException(
            status_code=400,
            detail="无效的Google商家URL。请提供有效的Google Maps商家分享链接。"
        )

    # 检查缓存（除非请求强制刷新或有自定义描述）
    cached_schema = None
    if not request.force_refresh:
        cached_schema = await cache.get(url)
        if cached_schema:
            logger.info(f"返回缓存结果: {url}")
            # 将缓存的模式转换为JSON-LD脚本格式
            schema_dict = cached_schema.model_dump(by_alias=True, exclude_none=True)
            schema_dict["@context"] = "https://schema.org"
            schema_dict["@type"] = "LocalBusiness"
            
            # 如果有自定义描述，直接覆盖缓存中的描述
            if request.description:
                schema_dict["description"] = request.description
            
            import json
            json_content = json.dumps(schema_dict, indent=2, ensure_ascii=False)
            script_content = f'<script type="application/ld+json">\n{json_content}\n</script>'

            return {
                "success": True,
                "script": script_content,
                "cached": True,
                "extracted_at": datetime.now().isoformat()
            }

    try:
        # 检查全局爬虫实例的浏览器状态
        if not crawler.browser or not crawler.browser.is_connected():
            logger.warning("全局浏览器实例已断开，尝试重新启动...")
            try:
                await crawler.stop()
                await crawler.start()
                logger.info("全局浏览器实例重启成功")
            except Exception as restart_error:
                logger.error(f"重启全局浏览器实例失败: {restart_error}")
                raise Exception(f"浏览器重启失败: {restart_error}")
        
        # 使用全局爬虫实例提取商家信息
        business_data = await crawler.extract_business_info(url)

        # 生成带有<script>标签的JSON-LD脚本
        json_ld_script = schema_generator.generate_json_ld_script(business_data, url, request.description)

        # 生成用于缓存的模式
        schema = schema_generator.generate_schema(business_data, url, request.description)
        await cache.set(url, schema)

        logger.info(f"成功提取并缓存商家信息: {schema.name}")

        return {
            "success": True,
            "script": json_ld_script,
            "cached": False,
            "extracted_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"提取商家信息时发生错误 {url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_at": datetime.now().isoformat()
        }


@app.delete("/api/cache/all")
async def clear_all_cache():
    """清除所有缓存条目
    
    删除缓存中的所有商家信息记录，释放存储空间。
    通常用于开发调试或系统维护。
    
    Returns:
        dict: 包含清除记录数量的响应消息
        
    Warning:
        此操作不可逆，会清除所有已缓存的商家数据
    """
    count = await cache.clear_all()
    logger.info(f"已清除所有缓存: {count} 条记录")
    return {"message": f"已清除 {count} 条缓存记录"}


@app.delete("/api/cache/expired")
async def cleanup_expired_cache():
    """手动清理过期缓存条目
    
    主动清理已过期的缓存记录，释放存储空间。
    虽然系统会自动清理过期缓存，但此端点允许手动触发清理。
    
    Returns:
        dict: 包含以下字段的响应：
            - message: 清理结果描述
            - expired_count: 清理的过期记录数量
    """
    expired_count = await cache.cleanup_expired()
    logger.info(f"手动清理已移除 {expired_count} 条过期缓存记录")
    return {
        "message": f"已清理 {expired_count} 条过期缓存记录",
        "expired_count": expired_count
    }


@app.get("/api/cache/stats")
async def get_cache_stats():
    """获取缓存系统统计信息
    
    返回缓存的详细统计数据，用于监控缓存性能和使用情况。
    
    Returns:
        dict: 缓存统计信息，包括：
            - active_entries: 活跃缓存条目数
            - hit_rate: 缓存命中率
            - total_hits: 总命中次数
            - total_misses: 总未命中次数
            - memory_usage: 内存使用情况（内存缓存）
    """
    stats = await cache.get_stats()
    return stats


@app.get("/api/stats")
async def get_api_stats():
    """获取完整的API统计信息
    
    返回包括当前统计、时间线数据和端点统计的完整API使用情况。
    适用于管理面板和监控系统的综合数据展示。
    
    Returns:
        dict: 包含以下字段的完整统计信息：
            - current_stats: 当前实时统计数据
            - timeline_data: 历史时间线数据
            - endpoint_stats: 各端点详细统计
    """
    return {
        "current_stats": api_stats.get_current_stats(),
        "timeline_data": api_stats.get_timeline_data(),
        "endpoint_stats": api_stats.get_endpoint_stats()
    }


@app.get("/api/stats/current")
async def get_current_stats():
    """获取当前实时统计数据
    
    返回当前时刻的API使用统计信息，包括请求数量、
    成功率、平均响应时间等关键指标。
    
    Returns:
        dict: 当前统计数据，包括：
            - total_requests: 总请求数
            - success_count: 成功请求数
            - error_count: 失败请求数
            - success_rate: 成功率百分比
            - avg_response_time: 平均响应时间
    """
    return api_stats.get_current_stats()


@app.get("/api/stats/timeline")
async def get_timeline_stats(points: int = 60):
    """获取时间线统计数据
    
    返回指定数量的历史统计数据点，用于绘制趋势图表。
    数据按时间顺序排列，适用于监控面板的图表展示。
    
    Args:
        points: 返回的数据点数量，默认60个点，最多支持1000个点
        
    Returns:
        dict: 时间线统计数据，包含时间戳和对应的统计指标数组
    """
    return api_stats.get_timeline_data(points=points)


@app.get("/api/stats/endpoints")
async def get_endpoint_stats():
    """获取各API端点的详细统计信息
    
    返回每个API端点的访问次数、响应时间等统计数据。
    用于分析各端点的使用情况和性能表现。
    
    Returns:
        dict: 各端点的统计信息，包括：
            - 端点路径为键的字典
            - 每个端点包含请求数、平均响应时间、错误率等指标
    """
    return api_stats.get_endpoint_stats()


@app.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket):
    """WebSocket端点，用于实时推送统计数据
    
    建立WebSocket连接，实时向客户端推送API统计信息更新。
    适用于实时监控面板和动态图表更新。
    
    Args:
        websocket: WebSocket连接对象
        
    Note:
        - 连接建立后会立即发送当前统计数据
        - 每次API调用后会自动推送更新的统计信息
        - 连接断开时会自动清理资源
    """
    await websocket.accept()
    logger.info(f"WebSocket连接已建立: {websocket.client}")
    await api_stats.add_websocket(websocket)
    
    try:
        while True:
            # 保持连接活跃，等待客户端消息
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接已断开: {websocket.client}")
        api_stats.remove_websocket(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
        api_stats.remove_websocket(websocket)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """应用程序健康检查端点
    
    检查应用程序的运行状态，包括缓存系统状态和基本统计信息。
    同时执行过期缓存清理操作，确保系统健康运行。
    
    功能特性：
    - 检查应用程序基本运行状态
    - 获取缓存系统统计信息
    - 自动清理过期缓存条目
    - 返回标准化的健康检查响应
    
    Returns:
        HealthResponse: 包含以下字段的健康检查响应：
            - status: 应用状态（"healthy"）
            - timestamp: 检查时间戳
            - version: 应用版本号
            - cache_size: 当前缓存条目数量
    """
    # 清理过期的缓存条目
    expired_count = await cache.cleanup_expired()
    if expired_count > 0:
        logger.info(f"健康检查时清理了 {expired_count} 条过期缓存记录")

    stats = await cache.get_stats()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        cache_size=stats['active_entries']
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """自定义404错误处理器
    
    处理未找到的端点请求，返回友好的错误信息。
    记录访问日志用于调试和监控。
    
    Args:
        request: HTTP请求对象，包含请求URL和方法
        exc: 404异常对象
        
    Returns:
        JSONResponse: 包含错误详情的404响应
    """
    logger.warning(f"404错误 - 未找到端点: {request.url}")
    return JSONResponse(
        status_code=404,
        content={"detail": "端点未找到"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """自定义500服务器内部错误处理器
    
    处理服务器内部错误，记录详细错误信息并返回通用错误响应。
    确保敏感信息不会泄露给客户端。
    
    Args:
        request: HTTP请求对象，包含请求上下文
        exc: 服务器内部异常对象
        
    Returns:
        JSONResponse: 包含通用错误信息的500响应
        
    Note:
        详细错误信息仅记录在服务器日志中，不返回给客户端
    """
    logger.error(f"服务器内部错误: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # 开发环境下直接运行服务器
    logger.info("启动开发服务器...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
