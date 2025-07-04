"""API统计模块

提供实时API请求统计功能，包括请求数量、成功数量和失败数量的跟踪。
"""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import json
from fastapi import WebSocket


class APIStats:
    """API统计类
    
    跟踪API请求的统计信息，包括总数、成功数、失败数等。
    支持时间窗口统计和实时数据推送，提供WebSocket实时监控功能。
    
    Features:
        - 实时请求统计跟踪
        - 滑动时间窗口分析
        - WebSocket实时数据推送
        - 端点级别统计
        - 响应时间监控
        - 自动数据清理
    
    Attributes:
        window_minutes: 时间窗口大小（分钟）
        requests_timeline: 请求时间线数据
        total_requests: 总请求数
        total_success: 总成功数
        total_failures: 总失败数
        websocket_connections: WebSocket连接列表
    """
    
    def __init__(self, window_minutes: int = 60):
        """初始化API统计对象
        
        设置时间窗口和初始化统计数据结构。
        
        Args:
            window_minutes: 时间窗口大小（分钟），默认60分钟
        """
        self.window_minutes = window_minutes
        self.window_seconds = window_minutes * 60
        
        # 使用deque存储时间序列数据，每个元素包含时间戳和统计信息
        self.requests_timeline = deque()  # (timestamp, endpoint, status)
        
        # 当前统计数据
        self.total_requests = 0
        self.total_success = 0
        self.total_failures = 0
        
        # WebSocket连接管理
        self.websocket_connections: List[WebSocket] = []
        
        # 启动清理任务
        self._cleanup_task = None
    
    def record_request(self, endpoint: str, success: bool, response_time: float = 0):
        """记录一次API请求
        
        将请求信息添加到统计数据中，更新计数器并触发实时数据推送。
        自动清理过期数据以维护时间窗口。
        
        Args:
            endpoint: API端点标识符
            success: 请求是否成功
            response_time: 响应时间（毫秒），默认为0
        """
        timestamp = time.time()
        
        # 记录到时间线
        self.requests_timeline.append({
            'timestamp': timestamp,
            'endpoint': endpoint,
            'success': success,
            'response_time': response_time
        })
        
        # 更新总计数器
        self.total_requests += 1
        if success:
            self.total_success += 1
        else:
            self.total_failures += 1
        
        # 清理过期数据
        self._cleanup_old_data()
        
        # 异步推送数据到WebSocket客户端
        asyncio.create_task(self._broadcast_stats())
    
    def _cleanup_old_data(self):
        """清理超出时间窗口的旧数据
        
        移除时间线中超出当前时间窗口的历史数据，
        确保统计数据始终在指定的时间范围内。
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        while self.requests_timeline and self.requests_timeline[0]['timestamp'] < cutoff_time:
            self.requests_timeline.popleft()
    
    def get_current_stats(self) -> Dict:
        """获取当前统计数据
        
        返回包含总体统计和时间窗口统计的完整数据。
        包括请求数量、成功率、失败数和平均响应时间。
        
        Returns:
            Dict: 包含以下字段的统计信息字典：
                - timestamp: 当前时间戳
                - total: 总体统计（所有时间）
                - window: 时间窗口内统计
                - window_minutes: 时间窗口大小
        """
        self._cleanup_old_data()
        
        # 计算时间窗口内的统计
        window_requests = len(self.requests_timeline)
        window_success = sum(1 for req in self.requests_timeline if req['success'])
        window_failures = window_requests - window_success
        
        # 计算平均响应时间
        if self.requests_timeline:
            avg_response_time = sum(req['response_time'] for req in self.requests_timeline) / len(self.requests_timeline)
        else:
            avg_response_time = 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total': {
                'requests': self.total_requests,
                'success': self.total_success,
                'failures': self.total_failures,
                'success_rate': (self.total_success / self.total_requests * 100) if self.total_requests > 0 else 0
            },
            'window': {
                'requests': window_requests,
                'success': window_success,
                'failures': window_failures,
                'success_rate': (window_success / window_requests * 100) if window_requests > 0 else 0,
                'avg_response_time': round(avg_response_time, 2)
            },
            'window_minutes': self.window_minutes
        }
    
    def get_timeline_data(self, points: int = 60) -> List[Dict]:
        """获取时间线数据用于图表展示
        
        将时间窗口分割为指定数量的时间点，
        计算每个时间点的请求统计数据。
        
        Args:
            points: 时间线数据点数量，默认60个点
            
        Returns:
            List[Dict]: 时间线数据列表，每个元素包含：
                - timestamp: 时间点
                - requests: 请求数量
                - success: 成功数量
                - failures: 失败数量
        """
        self._cleanup_old_data()
        
        if not self.requests_timeline:
            return []
        
        # 计算时间间隔
        current_time = time.time()
        start_time = current_time - self.window_seconds
        interval = self.window_seconds / points
        
        timeline_data = []
        
        for i in range(points):
            point_start = start_time + (i * interval)
            point_end = point_start + interval
            
            # 统计该时间段内的请求
            point_requests = 0
            point_success = 0
            point_failures = 0
            
            for req in self.requests_timeline:
                if point_start <= req['timestamp'] < point_end:
                    point_requests += 1
                    if req['success']:
                        point_success += 1
                    else:
                        point_failures += 1
            
            timeline_data.append({
                'timestamp': datetime.fromtimestamp(point_end).isoformat(),
                'requests': point_requests,
                'success': point_success,
                'failures': point_failures
            })
        
        return timeline_data
    
    def get_endpoint_stats(self) -> Dict[str, Dict]:
        """获取各端点的统计信息
        
        按端点分组统计请求数据，计算每个端点的
        成功率和平均响应时间。
        
        Returns:
            Dict[str, Dict]: 端点统计字典，键为端点名称，值包含：
                - requests: 请求总数
                - success: 成功数量
                - failures: 失败数量
                - success_rate: 成功率（百分比）
                - avg_response_time: 平均响应时间（毫秒）
        """
        self._cleanup_old_data()
        
        endpoint_stats = defaultdict(lambda: {'requests': 0, 'success': 0, 'failures': 0, 'total_response_time': 0})
        
        for req in self.requests_timeline:
            endpoint = req['endpoint']
            endpoint_stats[endpoint]['requests'] += 1
            endpoint_stats[endpoint]['total_response_time'] += req['response_time']
            
            if req['success']:
                endpoint_stats[endpoint]['success'] += 1
            else:
                endpoint_stats[endpoint]['failures'] += 1
        
        # 计算平均响应时间和成功率
        result = {}
        for endpoint, stats in endpoint_stats.items():
            result[endpoint] = {
                'requests': stats['requests'],
                'success': stats['success'],
                'failures': stats['failures'],
                'success_rate': (stats['success'] / stats['requests'] * 100) if stats['requests'] > 0 else 0,
                'avg_response_time': round(stats['total_response_time'] / stats['requests'], 2) if stats['requests'] > 0 else 0
            }
        
        return result
    
    async def add_websocket(self, websocket: WebSocket):
        """添加WebSocket连接
        
        将新的WebSocket连接添加到连接列表中，
        并立即发送当前统计数据。
        
        Args:
            websocket: WebSocket连接对象
        """
        self.websocket_connections.append(websocket)
        
        # 发送当前统计数据
        await self._send_stats_to_websocket(websocket)
    
    def remove_websocket(self, websocket: WebSocket):
        """移除WebSocket连接
        
        从连接列表中移除指定的WebSocket连接，
        通常在连接断开时调用。
        
        Args:
            websocket: 要移除的WebSocket连接对象
        """
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
    
    async def _send_stats_to_websocket(self, websocket: WebSocket):
        """向单个WebSocket连接发送统计数据
        
        构建包含当前统计、时间线和端点数据的消息，
        并发送到指定的WebSocket连接。
        
        Args:
            websocket: 目标WebSocket连接对象
            
        Note:
            如果发送失败（连接断开），会自动移除该连接
        """
        try:
            stats_data = {
                'type': 'stats_update',
                'data': {
                    'current_stats': self.get_current_stats(),
                    'timeline_data': self.get_timeline_data(),
                    'endpoint_stats': self.get_endpoint_stats()
                }
            }
            await websocket.send_text(json.dumps(stats_data))
        except Exception:
            # 连接已断开，移除它
            self.remove_websocket(websocket)
    
    async def _broadcast_stats(self):
        """向所有WebSocket连接广播统计数据
        
        构建统计数据消息并发送到所有活跃的WebSocket连接。
        自动检测并移除断开的连接。
        
        Note:
            此方法通常在记录新请求时自动调用，
            确保所有客户端都能实时接收到最新数据
        """
        if not self.websocket_connections:
            return
        
        # 创建要发送的数据
        stats_data = {
            'type': 'stats_update',
            'data': {
                'current_stats': self.get_current_stats(),
                'timeline_data': self.get_timeline_data(),
                'endpoint_stats': self.get_endpoint_stats()
            }
        }
        
        # 向所有连接发送数据
        disconnected_websockets = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(stats_data))
            except Exception:
                # 连接已断开，标记为需要移除
                disconnected_websockets.append(websocket)
        
        # 移除断开的连接
        for websocket in disconnected_websockets:
            self.remove_websocket(websocket)


# 全局统计实例
api_stats = APIStats(window_minutes=60)