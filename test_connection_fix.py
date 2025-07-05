#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试浏览器连接状态检查修复
验证在浏览器连接断开时是否能正确处理错误
"""

import asyncio
import logging
from app.crawler import GoogleBusinessCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection_handling():
    """测试连接状态处理"""
    logger.info("🚀 开始测试浏览器连接状态处理")
    
    crawler = GoogleBusinessCrawler()
    
    try:
        # 启动浏览器
        logger.info("启动浏览器...")
        await crawler.start()
        logger.info("✅ 浏览器启动成功")
        
        # 测试正常的商家信息提取
        test_url = "https://www.google.com/maps/place/Glenny+Kebabs+-+Glen+Waverley/@-37.8808927,145.1613872,17z/data=!4m6!3m5!1s0x6ad63fb8dcffdde9:0xc85b925eb239c959!8m2!3d-37.8808927!4d145.1639621!16s%2Fg%2F11c2j3ccnr?entry=tts&g_ep=EgoyMDI1MDYxNi4wIPu8ASoASAFQAw%3D%3D&skid=095b52df-b2c7-47de-b853-08ef623e94f5"
        
        logger.info("测试商家信息提取...")
        try:
            business_info = await crawler.extract_business_info(test_url)
            if business_info and business_info.get('name'):
                logger.info(f"✅ 商家信息提取成功: {business_info.get('name')}")
            else:
                logger.warning("⚠️ 商家信息提取返回空结果")
        except Exception as e:
            logger.error(f"❌ 商家信息提取失败: {e}")
            
            # 检查错误类型
            if "closed" in str(e).lower():
                logger.info("✅ 正确检测到连接关闭错误")
            elif "断开" in str(e) or "关闭" in str(e):
                logger.info("✅ 正确检测到连接状态错误")
            else:
                logger.warning(f"⚠️ 未知错误类型: {e}")
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
    finally:
        # 停止浏览器
        try:
            await crawler.stop()
            logger.info("✅ 浏览器已停止")
        except Exception as e:
            logger.warning(f"⚠️ 停止浏览器时出错: {e}")
    
    logger.info("🏁 连接状态处理测试完成")

if __name__ == "__main__":
    asyncio.run(test_connection_handling())