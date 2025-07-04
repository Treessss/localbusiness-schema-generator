#!/usr/bin/env python3
"""
独立的API监控服务器

可以在独立端口运行，专门用于监控主API服务器的统计数据。
"""

import os
import sys
import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logger.remove()

# 控制台日志
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>MONITOR</cyan> - <level>{message}</level>",
    level="INFO"
)

# 文件日志
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
logger.add(
    log_dir / "monitor.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | MONITOR - {message}",
    level="INFO",
    rotation="10 MB",
    retention="30 days",
    compression="zip"
)


class MonitorServer:
    """独立监控服务器类"""
    
    def __init__(self, api_host: str = "127.0.0.1", api_port: int = 8000):
        self.api_host = api_host
        self.api_port = api_port
        self.api_base_url = f"http://{api_host}:{api_port}"
        self.websocket_connections: List[WebSocket] = []
        self.stats_cache = {}
        self.last_update = 0
        self.update_interval =60  # 60秒更新一次
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title="API监控服务器",
            description="独立的API统计监控服务",
            version="1.0.0"
        )
        
        self.setup_routes()
        self.setup_middleware()
    
    def setup_middleware(self):
        """设置中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 挂载静态文件
        static_dir = Path("static")
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory="static"), name="static")
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/")
        async def root():
            """监控主页"""
            return FileResponse('static/monitor.html')
        
        @self.app.get("/api/stats")
        async def get_stats(force_refresh: bool = False):
            """获取API统计数据"""
            return await self.fetch_api_stats(force_refresh=force_refresh)

        
        @self.app.websocket("/ws/monitor")
        async def websocket_monitor(websocket: WebSocket):
            """WebSocket端点，用于实时推送监控数据"""
            try:
                await websocket.accept()
                self.websocket_connections.append(websocket)
                logger.info(f"新的监控连接，当前连接数: {len(self.websocket_connections)}")
                
                # 发送初始数据
                await self.send_stats_to_websocket(websocket)
                
                while True:
                    try:
                        # 设置接收超时，防止僵尸连接
                        message = await asyncio.wait_for(
                            websocket.receive_text(), 
                            timeout=30.0
                        )
                        # 处理心跳消息
                        if message == "ping":
                            await websocket.send_text("pong")
                    except asyncio.TimeoutError:
                        # 发送心跳检测
                        try:
                            await websocket.send_text(json.dumps({"type": "ping"}))
                        except Exception:
                            break
                    except Exception as e:
                        logger.debug(f"WebSocket接收消息错误: {e}")
                        break
                        
            except WebSocketDisconnect:
                logger.info(f"监控连接正常断开")
            except Exception as e:
                logger.error(f"WebSocket连接错误: {e}")
            finally:
                self.remove_websocket(websocket)
                logger.info(f"监控连接已清理，当前连接数: {len(self.websocket_connections)}")
    
    async def fetch_api_stats(self, force_refresh: bool = False) -> Dict:
        """从主API服务器获取统计数据"""
        current_time = time.time()
        
        # 检查缓存是否过期（除非强制刷新）
        if not force_refresh and current_time - self.last_update < self.update_interval and self.stats_cache:
            logger.debug("使用缓存的统计数据")
            return self.stats_cache
        
        if force_refresh:
            logger.info("强制刷新统计数据，跳过缓存")
        
        try:
            # 使用127.0.0.1而不是localhost，避免DNS解析问题
            api_url = self.api_base_url.replace('localhost', '127.0.0.1')
            
            headers = {
                "User-Agent": "MonitorServer/1.0",
                "Accept": "application/json",
                "Connection": "close"
            }
            
            print(f"正在请求API统计数据: {api_url}/api/stats")
            logger.info(f"正在请求API统计数据: {api_url}/api/stats")
            
            # 使用requests库进行同步请求
            response = requests.get(
                f"{api_url}/api/stats", 
                timeout=10.0,
                headers=headers,
                proxies=None
            )
            
            logger.info(f"API响应状态码: {response.status_code}")
            logger.info(f"API响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                self.stats_cache = response.json()
                self.last_update = current_time
                logger.debug("成功获取API统计数据")
                return self.stats_cache
            else:
                logger.warning(f"API服务器返回错误状态码: {response.status_code}")
                logger.warning(f"响应内容: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"无法连接到API服务器: {self.api_base_url}, 错误: {e}")
        except requests.exceptions.Timeout:
            logger.error("API服务器响应超时")
        except Exception as e:
            logger.error(f"获取统计数据失败: {e}")
        
        # 返回错误状态
        return {
            "error": "无法连接到API服务器",
            "api_url": self.api_base_url.replace('localhost', '127.0.0.1'),
            "timestamp": datetime.now().isoformat()
        }
    
    async def send_stats_to_websocket(self, websocket: WebSocket):
        """向单个WebSocket连接发送统计数据"""
        try:
            stats_data = await self.fetch_api_stats()
            message = {
                'type': 'monitor_update',
                'data': stats_data
            }
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"发送WebSocket数据失败: {e}")
            self.remove_websocket(websocket)
    
    async def broadcast_stats(self):
        """向所有WebSocket连接广播统计数据"""
        if not self.websocket_connections:
            return
        
        try:
            stats_data = await self.fetch_api_stats()
            message = {
                'type': 'monitor_update',
                'data': stats_data
            }
            
            disconnected_websockets = []
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.debug(f"WebSocket发送失败: {e}")
                    disconnected_websockets.append(websocket)
            
            # 移除断开的连接
            for websocket in disconnected_websockets:
                self.remove_websocket(websocket)
                
            if disconnected_websockets:
                logger.info(f"清理了 {len(disconnected_websockets)} 个断开的WebSocket连接")
                
        except Exception as e:
            logger.error(f"广播统计数据失败: {e}")
            # 不抛出异常，让定期任务继续运行
    
    def remove_websocket(self, websocket: WebSocket):
        """移除WebSocket连接"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
    
    async def start_background_tasks(self):
        """启动后台任务"""
        asyncio.create_task(self.periodic_broadcast())
    
    async def periodic_broadcast(self):
        """定期广播统计数据"""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                await self.broadcast_stats()
            except Exception as e:
                logger.error(f"定期广播任务出错: {e}")
                # 继续运行，不让单次错误导致整个任务停止
                await asyncio.sleep(5)  # 短暂等待后重试


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动API监控服务器')
    parser.add_argument('--port', type=int, default=8001, help='监控服务器端口 (默认: 8001)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监控服务器主机 (默认: 0.0.0.0)')
    parser.add_argument('--api-host', type=str, default='localhost', help='API服务器主机 (默认: localhost)')
    parser.add_argument('--api-port', type=int, default=8000, help='API服务器端口 (默认: 8000)')
    args = parser.parse_args()
    
    # 创建监控服务器
    monitor = MonitorServer(api_host=args.api_host, api_port=args.api_port)
    
    print("启动API监控服务器...")
    print(f"监控服务器地址: http://localhost:{args.port}")
    print(f"监控目标API: http://{args.api_host}:{args.api_port}")
    print("按Ctrl+C停止服务器")
    
    # 启动后台任务
    @monitor.app.on_event("startup")
    async def startup_event():
        await monitor.start_background_tasks()
        logger.info("监控服务器启动完成")
    
    # 启动服务器
    uvicorn.run(
        monitor.app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()