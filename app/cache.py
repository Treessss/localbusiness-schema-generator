"""商家数据缓存管理模块

提供Redis和内存两种缓存实现：
1. RedisCache - 基于Redis的分布式缓存，支持高并发
2. MemoryCache - 基于内存的本地缓存，适用于单机部署

缓存功能：
- 自动过期清理
- 命中率统计
- 缓存信息查询
- 批量清理操作
"""

import hashlib
import json
import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, falling back to memory cache")

from .models import LocalBusinessSchema, CacheInfo


class RedisCache:
    """基于Redis的分布式缓存实现
    
    提供高性能的分布式缓存服务，支持自动过期、连接池管理
    和统计信息收集。适用于多实例部署和高并发场景。
    
    Attributes:
        default_ttl_hours: 默认缓存过期时间（小时）
        redis_url: Redis连接URL
        redis_pool: Redis连接池
    """
    
    def __init__(self, default_ttl_hours: int = 24, redis_url: str = None):
        self.default_ttl_hours = default_ttl_hours
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_pool = None
        self._cleanup_task = None
        
        # 从环境变量获取连接池配置
        self.max_connections = int(os.getenv('REDIS_MAX_CONNECTIONS', '20'))
        self.socket_connect_timeout = int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5'))
        self.socket_timeout = int(os.getenv('REDIS_SOCKET_TIMEOUT', '5'))
        self.retry_on_timeout = os.getenv('REDIS_RETRY_ON_TIMEOUT', 'true').lower() == 'true'
        
        logger.info(f"初始化Redis缓存，TTL: {default_ttl_hours}小时，URL: {self.redis_url}")
        logger.info(f"Redis连接池配置: 最大连接数={self.max_connections}, 超时设置={self.socket_connect_timeout}s/{self.socket_timeout}s")
    
    async def _get_redis(self):
        """获取Redis连接实例
        
        创建或复用Redis连接池，确保连接的可用性和性能。
        
        Returns:
            redis.Redis: Redis客户端实例
            
        Raises:
            Exception: 连接Redis失败时抛出异常
        """
        if self.redis_pool is None:
            try:
                # 创建连接池
                self.redis_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    socket_connect_timeout=self.socket_connect_timeout,
                    socket_timeout=self.socket_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    decode_responses=True
                )
                
                # 创建Redis客户端
                redis_client = redis.Redis(connection_pool=self.redis_pool)
                
                # 测试连接
                await redis_client.ping()
                logger.info(f"Redis连接池已建立，最大连接数: {self.max_connections}")
                return redis_client
                
            except Exception as e:
                logger.error(f"连接Redis失败: {e}")
                raise
        else:
            # 返回新的Redis客户端实例，使用现有连接池
            return redis.Redis(connection_pool=self.redis_pool)
    
    def _generate_key(self, url: str) -> str:
        """从URL生成缓存键
        
        使用MD5哈希算法生成唯一的缓存键。
        
        Args:
            url: 商家URL
            
        Returns:
            str: 生成的缓存键
        """
        return f"business_cache:{hashlib.md5(url.encode()).hexdigest()}"
    
    def _generate_info_key(self, url: str) -> str:
        """生成缓存信息键
        
        为存储缓存元数据（如命中次数、过期时间等）生成专用键。
        
        Args:
            url: 商家URL
            
        Returns:
            str: 生成的缓存信息键
        """
        return f"business_info:{hashlib.md5(url.encode()).hexdigest()}"
    
    async def get(self, url: str) -> Optional[LocalBusinessSchema]:
        """获取缓存的商家数据
        
        从Redis中检索指定URL的商家信息，并更新命中统计。
        
        Args:
            url: 商家URL
            
        Returns:
            Optional[LocalBusinessSchema]: 商家数据对象，未找到时返回None
        """
        try:
            redis = await self._get_redis()
            key = self._generate_key(url)
            info_key = self._generate_info_key(url)
            
            # 获取缓存数据
            cached_data = await redis.get(key)
            if not cached_data:
                logger.debug(f"缓存未命中: {url}")
                return None
            
            # 更新命中次数
            await redis.hincrby(info_key, "hit_count", 1)
            
            logger.debug(f"缓存命中: {url}")
            data = json.loads(cached_data)
            return LocalBusinessSchema(**data)
            
        except Exception as e:
            logger.error(f"获取缓存时发生错误 {url}: {e}")
            return None
    
    async def set(self, url: str, schema: LocalBusinessSchema, ttl_hours: Optional[int] = None) -> None:
        """设置缓存条目
        
        将商家数据存储到Redis中，并设置过期时间和元数据。
        
        Args:
            url: 商家URL
            schema: 商家数据对象
            ttl_hours: 缓存过期时间（小时），默认使用实例设置
        """
        try:
            redis = await self._get_redis()
            key = self._generate_key(url)
            info_key = self._generate_info_key(url)
            ttl = ttl_hours or self.default_ttl_hours
            
            now = datetime.now()
            expires_at = now + timedelta(hours=ttl)
            
            # 存储数据
            data = json.dumps(schema.model_dump(), ensure_ascii=False)
            await redis.setex(key, ttl * 3600, data)  # TTL in seconds
            
            # 存储缓存信息
            cache_info = {
                "url": url,
                "cached_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "hit_count": "0"
            }
            await redis.hset(info_key, mapping=cache_info)
            await redis.expire(info_key, ttl * 3600)
            
            logger.info(f"已缓存商家数据: {url}, 过期时间: {expires_at}")
            
        except Exception as e:
            logger.error(f"设置缓存时发生错误 {url}: {e}")
    
    async def delete(self, url: str) -> bool:
        """删除指定URL的缓存条目
        
        从Redis中删除商家数据和相关元数据。
        
        Args:
            url: 商家URL
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        try:
            redis = await self._get_redis()
            key = self._generate_key(url)
            info_key = self._generate_info_key(url)
            
            result1 = await redis.delete(key)
            result2 = await redis.delete(info_key)
            
            if result1 or result2:
                logger.info(f"已删除缓存: {url}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除缓存时发生错误 {url}: {e}")
            return False
    
    async def clear_all(self) -> int:
        """清除所有缓存条目
        
        删除Redis中所有商家相关的缓存数据。
        
        Returns:
            int: 删除的条目数量
        """
        try:
            redis = await self._get_redis()
            
            # 查找所有相关的键
            business_keys = await redis.keys("business_cache:*")
            info_keys = await redis.keys("business_info:*")
            all_keys = business_keys + info_keys
            
            if all_keys:
                count = await redis.delete(*all_keys)
                logger.info(f"已清除所有缓存条目: {count} 项")
                return count
            return 0
            
        except Exception as e:
            logger.error(f"清除所有缓存时发生错误: {e}")
            return 0
    
    async def cleanup_expired(self) -> int:
        """清理过期缓存条目
        
        Redis会自动处理过期键，此方法仅为接口兼容性。
        
        Returns:
            int: 始终返回0，因为Redis自动处理过期
        """
        # Redis会自动清理过期的键，所以这里不需要手动清理
        return 0
    
    async def get_cache_info(self, url: str) -> Optional[CacheInfo]:
        """获取指定URL的缓存元数据信息
        
        检索缓存的详细信息，包括创建时间、过期时间和命中次数。
        
        Args:
            url: 商家URL
            
        Returns:
            Optional[CacheInfo]: 缓存信息对象，未找到时返回None
        """
        try:
            redis = await self._get_redis()
            info_key = self._generate_info_key(url)
            
            cache_info = await redis.hgetall(info_key)
            if not cache_info:
                return None
            
            return CacheInfo(
                url=cache_info['url'],
                cached_at=datetime.fromisoformat(cache_info['cached_at']),
                expires_at=datetime.fromisoformat(cache_info['expires_at']),
                hit_count=int(cache_info['hit_count'])
            )
            
        except Exception as e:
            logger.error(f"获取缓存信息时发生错误 {url}: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取Redis缓存统计信息
        
        收集并返回缓存的详细统计数据，包括条目数量和命中率。
        
        Returns:
            Dict[str, Any]: 包含统计信息的字典
        """
        try:
            redis = await self._get_redis()
            
            # 获取所有缓存键的数量
            business_keys = await redis.keys("business_cache:*")
            info_keys = await redis.keys("business_info:*")
            
            total_entries = len(business_keys)
            total_hits = 0
            
            # 计算总命中次数
            for info_key in info_keys:
                hit_count = await redis.hget(info_key, "hit_count")
                if hit_count:
                    total_hits += int(hit_count)
            
            return {
                'total_entries': total_entries,
                'active_entries': total_entries,  # Redis自动处理过期
                'expired_entries': 0,  # Redis自动处理过期
                'total_hits': total_hits,
                'hit_rate': total_hits / max(total_entries, 1)
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计信息时发生错误: {e}")
            return {
                'total_entries': 0,
                'active_entries': 0,
                'expired_entries': 0,
                'total_hits': 0,
                'hit_rate': 0.0
            }
    
    async def start_cleanup_task(self):
        """启动缓存清理任务
        
        Redis自动处理过期键，此方法仅为接口兼容性。
        """
        logger.info("Redis缓存无需清理任务（自动过期处理）")
    
    async def stop_cleanup_task(self):
        """停止缓存清理任务
        
        Redis不需要手动清理任务，此方法仅为接口兼容性。
        """
        logger.info("Redis缓存清理任务未运行")
    
    async def close(self):
        """关闭Redis连接池
        
        安全地关闭Redis连接池，释放所有连接资源。
        """
        if self.redis_pool:
            await self.redis_pool.disconnect()
            self.redis_pool = None
            logger.info("Redis连接池已关闭")


class MemoryCache:
    """基于内存的本地缓存实现
    
    提供高速的本地缓存服务，支持TTL过期机制和定时清理。
    适用于单机部署和开发环境。
    
    Attributes:
        _cache: 内存缓存字典
        default_ttl_hours: 默认缓存过期时间（小时）
        cleanup_interval_hours: 清理任务执行间隔（小时）
    """
    
    def __init__(self, default_ttl_hours: int = 24, cleanup_interval_hours: int = 1):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl_hours = default_ttl_hours
        self.cleanup_interval_hours = cleanup_interval_hours
        self._cleanup_task = None
        logger.info(f"初始化内存缓存，TTL: {default_ttl_hours}小时，清理间隔: {cleanup_interval_hours}小时")
    
    def _generate_key(self, url: str) -> str:
        """从URL生成缓存键
        
        使用MD5哈希算法生成唯一的缓存键。
        
        Args:
            url: 商家URL
            
        Returns:
            str: 生成的缓存键
        """
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存条目是否已过期
        
        比较当前时间与缓存条目的过期时间。
        
        Args:
            cache_entry: 缓存条目字典
            
        Returns:
            bool: 已过期返回True，否则返回False
        """
        expires_at = datetime.fromisoformat(cache_entry['expires_at'])
        return datetime.now() > expires_at
    
    def get(self, url: str) -> Optional[LocalBusinessSchema]:
        """获取缓存的商家数据
        
        从内存中检索指定URL的商家信息，自动处理过期检查。
        
        Args:
            url: 商家URL
            
        Returns:
            Optional[LocalBusinessSchema]: 商家数据对象，未找到或已过期时返回None
        """
        key = self._generate_key(url)
        
        if key not in self._cache:
            logger.debug(f"缓存未命中: {url}")
            return None
        
        cache_entry = self._cache[key]
        
        if self._is_expired(cache_entry):
            logger.debug(f"缓存已过期: {url}")
            del self._cache[key]
            return None
        
        # 更新命中次数
        cache_entry['hit_count'] += 1
        
        logger.debug(f"缓存命中: {url}")
        return LocalBusinessSchema(**cache_entry['data'])
    
    def set(self, url: str, schema: LocalBusinessSchema, ttl_hours: Optional[int] = None) -> None:
        """设置缓存条目
        
        将商家数据存储到内存中，并设置过期时间。
        
        Args:
            url: 商家URL
            schema: 商家数据对象
            ttl_hours: 缓存过期时间（小时），默认使用实例设置
        """
        key = self._generate_key(url)
        ttl = ttl_hours or self.default_ttl_hours
        
        now = datetime.now()
        expires_at = now + timedelta(hours=ttl)
        
        cache_entry = {
            'url': url,
            'data': schema.model_dump(),
            'cached_at': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'hit_count': 0
        }
        
        self._cache[key] = cache_entry
        logger.info(f"已缓存商家数据: {url}, 过期时间: {expires_at}")
    
    def delete(self, url: str) -> bool:
        """删除指定URL的缓存条目
        
        从内存中删除商家数据。
        
        Args:
            url: 商家URL
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        key = self._generate_key(url)
        
        if key in self._cache:
            del self._cache[key]
            logger.info(f"已删除缓存: {url}")
            return True
        
        return False
    
    def clear_all(self) -> int:
        """清除所有缓存条目
        
        删除内存中所有商家缓存数据。
        
        Returns:
            int: 删除的条目数量
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"已清除所有缓存条目: {count} 项")
        return count
    
    def cleanup_expired(self) -> int:
        """清理过期的缓存条目
        
        扫描并删除所有已过期的缓存条目。
        
        Returns:
            int: 清理的过期条目数量
        """
        expired_keys = []
        
        for key, cache_entry in self._cache.items():
            if self._is_expired(cache_entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"已清理 {len(expired_keys)} 条过期缓存记录")
        
        return len(expired_keys)
    
    def get_cache_info(self, url: str) -> Optional[CacheInfo]:
        """获取指定URL的缓存元数据信息
        
        检索缓存的详细信息，包括创建时间、过期时间和命中次数。
        
        Args:
            url: 商家URL
            
        Returns:
            Optional[CacheInfo]: 缓存信息对象，未找到时返回None
        """
        key = self._generate_key(url)
        
        if key not in self._cache:
            return None
        
        cache_entry = self._cache[key]
        
        return CacheInfo(
            url=cache_entry['url'],
            cached_at=datetime.fromisoformat(cache_entry['cached_at']),
            expires_at=datetime.fromisoformat(cache_entry['expires_at']),
            hit_count=cache_entry['hit_count']
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取内存缓存统计信息
        
        收集并返回缓存的详细统计数据，包括条目数量、过期条目和命中率。
        
        Returns:
            Dict[str, Any]: 包含统计信息的字典
        """
        total_entries = len(self._cache)
        expired_count = 0
        total_hits = 0
        
        for cache_entry in self._cache.values():
            if self._is_expired(cache_entry):
                expired_count += 1
            total_hits += cache_entry['hit_count']
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_count,
            'expired_entries': expired_count,
            'total_hits': total_hits,
            'hit_rate': total_hits / max(total_entries, 1)
        }
    
    async def start_cleanup_task(self):
        """启动定时清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info(f"已启动缓存清理任务，每 {self.cleanup_interval_hours} 小时运行一次")
    
    async def stop_cleanup_task(self):
        """停止定时清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("已停止缓存清理任务")
    
    async def _periodic_cleanup(self):
        """定期清理过期缓存的后台任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)  # 转换为秒
                expired_count = self.cleanup_expired()
                if expired_count > 0:
                    logger.info(f"定期清理已移除 {expired_count} 条过期缓存记录")
            except asyncio.CancelledError:
                logger.info("缓存清理任务已取消")
                break
            except Exception as e:
                logger.error(f"定期缓存清理时发生错误: {e}")
                # 继续运行，不要因为单次错误而停止清理任务


# 创建缓存实例的工厂函数
def create_cache_instance():
    """根据环境配置创建合适的缓存实例
    
    根据环境变量和Redis可用性自动选择Redis或内存缓存实现。
    
    Returns:
        Union[RedisCache, MemoryCache]: 缓存实例
    """
    use_redis = os.getenv('USE_REDIS', 'true').lower() == 'true'
    
    if use_redis and REDIS_AVAILABLE:
        try:
            return RedisCache()
        except Exception as e:
            logger.error(f"创建Redis缓存失败，回退到内存缓存: {e}")
            return MemoryCache()
    else:
        if use_redis and not REDIS_AVAILABLE:
            logger.warning("请求使用Redis但不可用，使用内存缓存")
        return MemoryCache()

# 全局缓存实例
cache = create_cache_instance()