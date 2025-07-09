"""基于Redis的分布式并发限制器

实现并发连接数控制，支持：
1. 基于IP地址的并发限制
2. 基于用户标识的并发限制
3. 不同接口的独立并发配置
4. 友好的错误信息返回
5. 并发状态查询
6. 自动清理超时连接
"""

import time
import json
import uuid
import os
from typing import Optional, Dict, Any, AsyncContextManager
from datetime import datetime, timedelta
import redis.asyncio as redis
from loguru import logger
import asyncio
from contextlib import asynccontextmanager


class ConcurrencyLimitExceeded(Exception):
    """并发限制异常"""
    def __init__(self, message: str, retry_after: int = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


class RedisConcurrencyLimiter:
    """基于Redis的分布式并发限制器
    
    使用Redis SET和过期时间实现并发连接数控制。
    支持多种并发策略和友好的错误信息。
    """
    
    def __init__(self, redis_url: str = None):
        """
        初始化并发限制器
        
        Args:
            redis_url: Redis连接URL
        """
        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client = None
        
        # 从环境变量读取并发限制配置
        cache_limit = int(os.getenv("CACHE_CONCURRENCY_LIMIT", "1000"))
        crawler_limit = int(os.getenv("CRAWLER_CONCURRENCY_LIMIT", "50"))
        concurrency_timeout = int(os.getenv("CONCURRENCY_TIMEOUT", "300"))
        
        self.limits = {
            "cache_requests": {
                "limit": cache_limit,
                "timeout": concurrency_timeout,
                "description": "缓存请求"
            },
            "crawler_requests": {
                "limit": crawler_limit,
                "timeout": concurrency_timeout * 4,  # 爬虫请求超时时间更长
                "description": "爬虫请求"
            }
        }
        
        logger.info(
            f"初始化Redis并发限制器，URL: {self.redis_url}, "
            f"缓存并发限制: {cache_limit}, 爬虫并发限制: {crawler_limit}, "
            f"超时时间: {concurrency_timeout}秒"
        )
    
    async def _get_redis(self):
        """获取Redis连接"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        return self.redis_client
    
    def _get_key(self, identifier: str, limit_type: str) -> str:
        """生成Redis键名"""
        return f"concurrency:{limit_type}:{identifier}"
    
    def _get_connection_key(self, identifier: str, limit_type: str, connection_id: str) -> str:
        """生成连接键名"""
        return f"conn:{limit_type}:{identifier}:{connection_id}"
    
    def _extract_client_id(self, request) -> str:
        """提取客户端标识
        
        优先级：
        1. X-Client-ID 头部
        2. X-Forwarded-For 头部（代理IP）
        3. 客户端IP地址
        """
        # 检查自定义客户端ID头部
        client_id = request.headers.get("X-Client-ID")
        if client_id:
            return f"client:{client_id}"
        
        # 检查代理IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个IP（真实客户端IP）
            real_ip = forwarded_for.split(",")[0].strip()
            return f"ip:{real_ip}"
        
        # 使用客户端IP
        client_ip = getattr(request.client, 'host', 'unknown')
        return f"ip:{client_ip}"
    
    async def _cleanup_expired_connections(self, key: str, timeout: int):
        """清理过期的连接"""
        redis_client = await self._get_redis()
        current_time = int(time.time())
        cutoff_time = current_time - timeout
        
        try:
            # 获取所有连接
            connections = await redis_client.smembers(key)
            expired_connections = []
            
            for conn in connections:
                # 检查连接的时间戳
                conn_key = f"{key}:meta:{conn}"
                conn_time = await redis_client.get(conn_key)
                
                if conn_time is None or int(conn_time) < cutoff_time:
                    expired_connections.append(conn)
            
            # 批量删除过期连接
            if expired_connections:
                pipe = redis_client.pipeline()
                for conn in expired_connections:
                    pipe.srem(key, conn)
                    pipe.delete(f"{key}:meta:{conn}")
                await pipe.execute()
                
                logger.debug(f"清理了 {len(expired_connections)} 个过期连接")
                
        except redis.RedisError as e:
            logger.error(f"清理过期连接失败: {e}")
    
    @asynccontextmanager
    async def acquire_connection(self, request, limit_type: str):
        """获取并发连接（上下文管理器）
        
        Args:
            request: FastAPI请求对象
            limit_type: 限制类型（cache_requests 或 crawler_requests）
            
        Yields:
            str: 连接ID
            
        Raises:
            ConcurrencyLimitExceeded: 当超过并发限制时抛出
        """
        if limit_type not in self.limits:
            raise ValueError(f"未知的限制类型: {limit_type}")
        
        config = self.limits[limit_type]
        client_id = self._extract_client_id(request)
        key = self._get_key(client_id, limit_type)
        connection_id = str(uuid.uuid4())
        
        redis_client = await self._get_redis()
        current_time = int(time.time())
        
        connection_added = False
        try:
            # 清理过期连接
            await self._cleanup_expired_connections(key, config["timeout"])
            
            # 使用Redis Lua脚本实现原子性的并发检查和连接添加
            # 这样可以避免竞态条件
            lua_script = """
            local key = KEYS[1]
            local connection_id = ARGV[1]
            local limit = tonumber(ARGV[2])
            local current_time = ARGV[3]
            local timeout = tonumber(ARGV[4])
            
            -- 获取当前连接数
            local current_count = redis.call('SCARD', key)
            
            -- 检查是否超过限制
            if current_count >= limit then
                return {"error", current_count}
            end
            
            -- 原子性地添加连接
            redis.call('SADD', key, connection_id)
            redis.call('SET', key .. ':meta:' .. connection_id, current_time, 'EX', timeout + 60)
            redis.call('EXPIRE', key, timeout + 60)
            
            return {"success", current_count + 1}
            """
            
            result = await redis_client.eval(
                lua_script,
                1,  # 键的数量
                key,  # KEYS[1]
                connection_id,  # ARGV[1]
                str(config["limit"]),  # ARGV[2]
                str(current_time),  # ARGV[3]
                str(config["timeout"])  # ARGV[4]
            )
            
            if result[0] == "error":
                current_count = result[1]
                
                # 根据限制类型提供不同的建议
                if limit_type == "cache_requests":
                    error_msg = (
                        f"缓存请求并发数已达上限 ({current_count}/{config['limit']})。"
                        f"缓存请求通常处理较快，建议稍后重试。"
                    )
                    retry_after = 3
                elif limit_type == "crawler_requests":
                    error_msg = (
                        f"爬虫请求并发数已达上限 ({current_count}/{config['limit']})。"
                        f"爬虫请求处理时间较长，建议等待更长时间后重试，或优先使用缓存数据。"
                    )
                    retry_after = 10
                else:
                    error_msg = (
                        f"{config['description']}并发数已达上限，"
                        f"当前并发: {current_count}/{config['limit']}。"
                        f"请稍后重试。"
                    )
                    retry_after = 5
                
                logger.warning(
                    f"并发限制触发 - 客户端: {client_id}, 类型: {limit_type}, "
                    f"当前: {current_count}/{config['limit']}, 建议等待: {retry_after}秒"
                )
                
                raise ConcurrencyLimitExceeded(error_msg, retry_after=retry_after)
            
            # 连接成功添加
            connection_added = True
            new_count = result[1]
            
            logger.debug(
                f"获取并发连接 - 客户端: {client_id}, 类型: {limit_type}, "
                f"连接ID: {connection_id}, 当前并发: {new_count}/{config['limit']}"
            )
            
            try:
                yield connection_id
            finally:
                # 只有成功添加连接后才尝试释放
                if connection_added:
                    await self._release_connection(key, connection_id)
                
        except ConcurrencyLimitExceeded:
            # 重新抛出并发限制异常
            raise
        except redis.RedisError as e:
            logger.error(f"Redis并发检查失败: {e}")
            # 如果连接已添加但Redis操作失败，尝试清理
            if connection_added:
                try:
                    await self._release_connection(key, connection_id)
                except Exception as cleanup_error:
                    logger.error(f"清理失败的连接时出错: {cleanup_error}")
            
            # Redis故障时抛出异常，确保并发控制的有效性
            raise ConcurrencyLimitExceeded(
                "并发控制服务暂时不可用，请稍后重试",
                retry_after=10
            )
        except Exception as e:
            logger.error(f"并发限制器意外错误: {e}")
            # 如果连接已添加但发生其他异常，尝试清理
            if connection_added:
                try:
                    await self._release_connection(key, connection_id)
                except Exception as cleanup_error:
                    logger.error(f"清理失败的连接时出错: {cleanup_error}")
            
            # 其他异常也转换为并发限制异常，确保一致的错误处理
            raise ConcurrencyLimitExceeded(
                "并发控制服务发生错误，请稍后重试",
                retry_after=5
            )
    
    async def _release_connection(self, key: str, connection_id: str):
        """释放连接"""
        redis_client = await self._get_redis()
        
        try:
            pipe = redis_client.pipeline()
            pipe.srem(key, connection_id)
            pipe.delete(f"{key}:meta:{connection_id}")
            await pipe.execute()
            
            logger.debug(f"释放并发连接: {connection_id}")
            
        except redis.RedisError as e:
            logger.error(f"释放连接失败: {e}")
    
    async def get_concurrency_status(self, request, limit_type: str) -> Dict[str, Any]:
        """获取并发状态
        
        Args:
            request: FastAPI请求对象
            limit_type: 限制类型
            
        Returns:
            dict: 当前并发状态
        """
        if limit_type not in self.limits:
            return {"error": f"未知的限制类型: {limit_type}"}
        
        config = self.limits[limit_type]
        client_id = self._extract_client_id(request)
        key = self._get_key(client_id, limit_type)
        
        redis_client = await self._get_redis()
        
        try:
            # 清理过期连接
            await self._cleanup_expired_connections(key, config["timeout"])
            
            # 获取当前并发数
            current_count = await redis_client.scard(key)
            remaining = max(0, config["limit"] - current_count)
            
            return {
                "limit_type": limit_type,
                "description": config["description"],
                "limit": config["limit"],
                "timeout": config["timeout"],
                "current_count": current_count,
                "remaining": remaining,
                "is_limited": current_count >= config["limit"],
                "timestamp": datetime.now().isoformat()
            }
            
        except redis.RedisError as e:
            logger.error(f"获取并发状态失败: {e}")
            return {
                "error": f"获取并发状态失败: {str(e)}",
                "limit_type": limit_type
            }
    
    async def get_all_concurrency_status(self, request) -> Dict[str, Any]:
        """获取所有限制类型的并发状态"""
        client_id = self._extract_client_id(request)
        status = {
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "limits": {}
        }
        
        for limit_type in self.limits.keys():
            status["limits"][limit_type] = await self.get_concurrency_status(request, limit_type)
        
        return status
    
    async def force_cleanup_connections(self, request, limit_type: str) -> Dict[str, Any]:
        """强制清理所有连接（用于故障恢复）
        
        Args:
            request: FastAPI请求对象
            limit_type: 限制类型
            
        Returns:
            dict: 清理结果
        """
        if limit_type not in self.limits:
            return {"error": f"未知的限制类型: {limit_type}"}
        
        config = self.limits[limit_type]
        client_id = self._extract_client_id(request)
        key = self._get_key(client_id, limit_type)
        
        redis_client = await self._get_redis()
        
        try:
            # 获取所有连接
            connections = await redis_client.smembers(key)
            cleaned_count = 0
            
            if connections:
                pipe = redis_client.pipeline()
                for conn in connections:
                    pipe.srem(key, conn)
                    pipe.delete(f"{key}:meta:{conn}")
                    cleaned_count += 1
                
                # 删除主键
                pipe.delete(key)
                await pipe.execute()
            
            logger.info(
                f"强制清理连接完成 - 客户端: {client_id}, 类型: {limit_type}, "
                f"清理数量: {cleaned_count}"
            )
            
            return {
                "success": True,
                "cleaned_count": cleaned_count,
                "limit_type": limit_type,
                "client_id": client_id
            }
            
        except redis.RedisError as e:
            logger.error(f"强制清理连接失败: {e}")
            return {
                "error": f"强制清理连接失败: {str(e)}",
                "limit_type": limit_type
            }
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Redis并发限制器连接已关闭")