"""中间件模块

提供API请求统计中间件，自动跟踪所有API请求的统计信息。
"""

import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .stats import api_stats
import logging

logger = logging.getLogger(__name__)


class StatsMiddleware(BaseHTTPMiddleware):
    """API统计中间件
    
    自动跟踪所有API请求，记录请求数量、成功数量、失败数量和响应时间。
    专门针对POST /api/extract接口进行统计，提供详细的性能监控数据。
    
    Features:
        - 自动记录请求统计信息
        - 计算响应时间
        - 区分成功和失败请求
        - 添加响应时间头部
        - 异常处理和错误记录
    """
    
    def __init__(self, app):
        """初始化统计中间件
        
        设置中间件以拦截和处理所有HTTP请求。
        
        Args:
            app: FastAPI应用实例
        """
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并记录统计信息
        
        拦截HTTP请求，记录统计信息并计算响应时间。
        仅对POST /api/extract接口进行统计跟踪。
        
        Args:
            request: HTTP请求对象
            call_next: 下一个中间件或路由处理器的调用函数
            
        Returns:
            Response: HTTP响应对象，包含响应时间头部
            
        Raises:
            Exception: 请求处理过程中的任何异常都会被捕获并记录
        """
        # 只统计 POST /api/extract 接口
        if not (request.method == "POST" and request.url.path == "/api/extract"):
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取端点信息
        endpoint = self._get_endpoint_name(request)
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算响应时间（毫秒）
            response_time = (time.time() - start_time) * 1000
            
            # 判断请求是否成功（2xx状态码）
            success = 200 <= response.status_code < 300
            
            # 记录统计信息
            api_stats.record_request(
                endpoint=endpoint,
                success=success,
                response_time=response_time
            )
            
            # 添加响应头
            response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            
            return response
            
        except Exception as e:
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000
            
            # 记录失败的请求
            api_stats.record_request(
                endpoint=endpoint,
                success=False,
                response_time=response_time
            )
            
            logger.error(f"请求处理异常: {endpoint} - {str(e)}")
            
            # 返回500错误响应
            return JSONResponse(
                status_code=500,
                content={"error": "内部服务器错误"},
                headers={"X-Response-Time": f"{response_time:.2f}ms"}
            )
    

    def _get_endpoint_name(self, request: Request) -> str:
        """获取API端点名称
        
        从请求对象中提取端点标识符，用于统计分类。
        优先使用路由信息，回退到URL路径。
        
        Args:
            request: HTTP请求对象
            
        Returns:
            str: 格式化的端点名称，如"POST /api/extract"
            
        Examples:
            >>> _get_endpoint_name(request)
            'POST /api/extract'
        """
        # 尝试获取路由信息
        if hasattr(request, 'scope') and 'route' in request.scope:
            route = request.scope['route']
            if hasattr(route, 'path'):
                return f"{request.method} {route.path}"
        
        # 回退到使用URL路径
        return f"{request.method} {request.url.path}"