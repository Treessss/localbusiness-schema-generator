#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试浏览器预热机制修复效果

这个脚本用于验证添加预热机制后，是否解决了需要先运行test_browser_basic.py的问题。
直接测试GoogleBusinessCrawler的启动和页面创建功能。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.crawler import GoogleBusinessCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def test_direct_crawler_start():
    """直接测试GoogleBusinessCrawler启动，不依赖test_browser_basic.py"""
    logger.info("=== 测试直接启动GoogleBusinessCrawler ===")
    
    crawler = None
    
    try:
        # 创建爬虫实例
        logger.info("创建GoogleBusinessCrawler实例...")
        crawler = GoogleBusinessCrawler()
        
        # 启动浏览器（包含预热机制）
        logger.info("启动浏览器（包含预热机制）...")
        await crawler.start()
        
        # 检查浏览器状态
        if crawler.browser and crawler.browser.is_connected():
            logger.info("✅ 浏览器启动成功并已连接")
        else:
            logger.error("❌ 浏览器启动失败或未连接")
            return False
        
        # 测试创建页面（这是之前卡住的地方）
        logger.info("测试创建新页面...")
        page = await crawler.browser.new_page()
        logger.info("✅ 页面创建成功")
        
        # 测试简单导航
        logger.info("测试页面导航...")
        await page.goto('https://www.google.com', wait_until='domcontentloaded', timeout=15000)
        title = await page.title()
        logger.info(f"✅ 页面导航成功，标题: {title}")
        
        # 关闭测试页面
        await page.close()
        logger.info("测试页面已关闭")
        
        logger.info("=== 直接启动测试成功 ===")
        return True
        
    except Exception as e:
        logger.error(f"❌ 直接启动测试失败: {e}")
        return False
        
    finally:
        if crawler:
            try:
                await crawler.stop()
                logger.info("爬虫实例已停止")
            except Exception as e:
                logger.warning(f"停止爬虫时出错: {e}")

async def test_business_extraction():
    """测试商家信息提取功能"""
    logger.info("=== 测试商家信息提取功能 ===")
    
    crawler = None
    
    try:
        # 使用异步上下文管理器
        async with GoogleBusinessCrawler() as crawler:
            logger.info("使用上下文管理器启动爬虫")
            
            # 测试URL
            test_url = "https://maps.app.goo.gl/XCLKuyn4vj9qrijE7"
            logger.info(f"测试提取商家信息: {test_url}")
            
            # 提取商家信息
            business_info = await crawler.extract_business_info(test_url)
            
            # 检查结果
            if business_info and business_info.get('name'):
                logger.info(f"✅ 商家信息提取成功")
                logger.info(f"商家名称: {business_info.get('name')}")
                logger.info(f"评分: {business_info.get('rating')}")
                logger.info(f"地址: {business_info.get('address')}")
                return True
            else:
                logger.error("❌ 商家信息提取失败或结果为空")
                return False
                
    except Exception as e:
        logger.error(f"❌ 商家信息提取测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"操作系统: {sys.platform}")
    logger.info("开始测试浏览器预热机制修复效果...")
    
    # 测试1: 直接启动爬虫
    test1_success = await test_direct_crawler_start()
    
    if test1_success:
        logger.info("基础启动测试通过，继续商家信息提取测试")
        
        # 测试2: 商家信息提取
        test2_success = await test_business_extraction()
        
        if test2_success:
            logger.info("🎉 所有测试通过！预热机制修复成功！")
            logger.info("现在可以直接使用GoogleBusinessCrawler，无需先运行test_browser_basic.py")
        else:
            logger.error("商家信息提取测试失败")
    else:
        logger.error("基础启动测试失败，预热机制可能需要进一步调整")

if __name__ == "__main__":
    asyncio.run(main())