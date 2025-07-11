"""Google商家Schema生成器的FastAPI应用程序

这个应用程序提供以下功能：
1. 从Google Maps商家页面提取商家信息
2. 生成符合Schema.org标准的结构化数据
3. 提供缓存机制以提高性能
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .models import (
    ExtractRequest,
    HealthResponse,
)
from .crawler import GoogleBusinessCrawler
from .schema_generator import SchemaGenerator
from .cache import cache
from .utils import is_google_business_url
from .middleware import StatsMiddleware
from .stats import api_stats
from app.concurrency_limiter import RedisConcurrencyLimiter, ConcurrencyLimitExceeded

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
try:
    log_dir.mkdir(exist_ok=True)  # 确保日志目录存在
    # 测试写入权限
    test_file = log_dir / "test_write.tmp"
    test_file.touch()
    test_file.unlink()  # 删除测试文件
    
    logger.add(
        log_dir / "app.log",
        rotation="1 day",  # 每天轮转一次
        retention="30 days",  # 保留30天的日志
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # 文件日志记录更详细的信息
        encoding="utf-8"  # 确保中文字符正确编码
    )
    logger.info("文件日志已启用")
except PermissionError:
    logger.warning("无法写入日志文件，仅使用控制台日志")
except Exception as e:
    logger.error(f"设置文件日志时出错: {e}，仅使用控制台日志")

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

# 初始化并发限制器（从环境变量获取Redis URL）
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
concurrency_limiter = RedisConcurrencyLimiter(redis_url=redis_url)


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

    # 关闭并发限制器连接
    try:
        await concurrency_limiter.close()
        logger.info("并发限制器连接已关闭")
    except Exception as e:
        logger.error(f"关闭并发限制器连接时出错: {e}")

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
async def extract_business_info(extract_request: ExtractRequest, request: Request):
    """提取Google商家信息并生成Schema.org结构化数据
    
    从Google Maps商家页面提取详细信息，生成符合Schema.org标准的
    JSON-LD结构化数据脚本。支持缓存机制和并发控制以提高性能。
    
    功能特性：
    - 自动验证Google Maps URL格式
    - 智能缓存机制，避免重复爬取
    - 支持自定义商家描述
    - 支持强制刷新缓存
    - 生成可直接嵌入HTML的JSON-LD脚本
    - 并发连接数控制，防止资源过载
    
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
        HTTPException: 当URL无效或并发限制时抛出错误
    """
    url = str(extract_request.url)
    logger.info(f"收到URL提取请求: {url}")

    # 验证URL格式是否为有效的Google商家URL
    if not is_google_business_url(url):
        logger.warning(f"无效的Google商家URL: {url}")
        raise HTTPException(
            status_code=400,
            detail="无效的Google商家URL。请提供有效的Google Maps商家分享链接。"
        )

    # 检查缓存（除非请求强制刷新）
    cached_schema = None
    if not extract_request.force_refresh:
        try:
            async with concurrency_limiter.acquire_connection(request,
                                                              "cache_requests") as cache_conn_id:
                logger.debug(f"获取缓存请求并发连接: {cache_conn_id}")
                cached_schema = await cache.get(url)

        except ConcurrencyLimitExceeded:
            # 重新抛出异常，让统一的异常处理器处理
            raise

    # 如果有缓存结果，直接返回
    if cached_schema:
        logger.info(f"返回缓存结果: {url}")
        # 将缓存的模式转换为JSON-LD脚本格式
        schema_dict = cached_schema.model_dump(by_alias=True, exclude_none=True)
        schema_dict["@context"] = "https://schema.org"
        schema_dict["@type"] = "LocalBusiness"

        # 如果有自定义描述，直接覆盖缓存中的描述
        if extract_request.description:
            schema_dict["description"] = extract_request.description

        import json
        json_content = json.dumps(schema_dict, indent=2, ensure_ascii=False)
        script_content = f'<script type="application/ld+json">\n{json_content}\n</script>'

        return {
            "success": True,
            "script": script_content,
            "cached": True,
            "extracted_at": datetime.now().isoformat()
        }

    # 需要爬取数据时，使用爬虫并发限制
    try:
        async with concurrency_limiter.acquire_connection(request,
                                                          "crawler_requests") as crawler_conn_id:
            logger.info(f"获取爬虫请求并发连接: {crawler_conn_id}")

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
            json_ld_script = schema_generator.generate_json_ld_script(business_data, url,
                                                                      extract_request.description)

            # 生成用于缓存的模式
            schema = schema_generator.generate_schema(business_data, url,
                                                      extract_request.description)
            await cache.set(url, schema)

            logger.info(f"成功提取并缓存商家信息: {schema.name}")

            return {
                "success": True,
                "script": json_ld_script,
                "cached": False,
                "extracted_at": datetime.now().isoformat()
            }

    except ConcurrencyLimitExceeded:
        # 重新抛出异常，让统一的异常处理器处理
        raise
    except Exception as e:
        logger.error(f"提取商家信息时发生错误 {url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_at": datetime.now().isoformat()
        }


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


@app.get("/api/concurrency-status")
async def get_concurrency_status(request: Request):
    """获取当前客户端的并发状态
    
    返回当前客户端在各种并发限制类型下的使用情况，包括：
    - 并发限制是否启用
    - 当前并发数和剩余配额
    - 超时设置
    - 是否当前受限
    
    Returns:
        dict: 包含所有并发限制类型状态的详细信息
    """
    try:
        status = await concurrency_limiter.get_all_concurrency_status(request)
        return {
            "success": True,
            "concurrency_limit_enabled": True,
            **status
        }
    except Exception as e:
        logger.error(f"获取并发状态失败: {e}")
        return {
            "success": False,
            "concurrency_limit_enabled": False,
            "error": str(e)
        }


@app.post("/api/concurrency-cleanup")
async def force_cleanup_concurrency(request: Request, limit_type: str):
    """强制清理并发连接（管理端点）
    
    用于故障恢复，强制清理指定类型的所有并发连接。
    当并发计数出现异常时（如显示5/1这种情况），可以使用此端点重置。
    
    Args:
        request: HTTP请求对象
        limit_type: 要清理的限制类型（cache_requests 或 crawler_requests）
    
    Returns:
        dict: 清理结果，包括清理的连接数量
        
    Warning:
        此操作会强制清理所有连接，可能影响正在进行的请求
    """
    try:
        result = await concurrency_limiter.force_cleanup_connections(request, limit_type)
        if result.get("success"):
            logger.info(
                f"管理员强制清理并发连接 - 类型: {limit_type}, "
                f"清理数量: {result.get('cleaned_count', 0)}"
            )
        return result
    except Exception as e:
        logger.error(f"强制清理并发连接失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "limit_type": limit_type
        }


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


@app.exception_handler(ConcurrencyLimitExceeded)
async def concurrency_limit_handler(request: Request, exc: ConcurrencyLimitExceeded):
    """并发限制异常处理器
    
    统一处理所有并发限制异常，返回标准化的错误响应格式。
    确保所有并发限制触发时都返回一致的用户友好信息。
    
    Args:
        request: HTTP请求对象
        exc: 并发限制异常对象
        
    Returns:
        JSONResponse: 标准化的429响应，包含详细的错误信息和重试建议
    """
    from datetime import datetime

    # 从异常消息中提取限制类型
    limit_type = "unknown"
    if "缓存请求" in str(exc):
        limit_type = "cache_requests"
        limit_description = "缓存请求"
    elif "爬虫请求" in str(exc):
        limit_type = "crawler_requests"
        limit_description = "爬虫请求"
    else:
        limit_description = "请求"

    response_content = {
        "success": False,
        "error": "并发限制已达上限",
        "message": str(exc),
        "error_code": "CONCURRENCY_LIMIT_EXCEEDED",
        "limit_type": limit_type,
        "limit_description": limit_description,
        "retry_suggestion": f"请等待 {exc.retry_after} 秒后重试",
        "timestamp": datetime.now().isoformat()
    }

    return JSONResponse(
        status_code=429,
        content=response_content,
        headers={"Retry-After": str(exc.retry_after)}
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
