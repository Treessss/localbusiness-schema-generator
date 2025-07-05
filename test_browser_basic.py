#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础浏览器测试脚本
用于诊断Linux环境下的浏览器连接问题
"""

import asyncio
import logging
import sys
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_basic_browser():
    """测试基础浏览器功能"""
    logger.info("=== 基础浏览器测试开始 ===")
    
    playwright = None
    browser = None
    page = None
    
    try:
        # 启动Playwright
        logger.info("启动Playwright...")
        playwright = await async_playwright().start()
        logger.info("Playwright启动成功")
        
        # 最基本的浏览器参数
        basic_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage'
        ]
        
        # 启动浏览器
        logger.info("启动浏览器...")
        browser = await playwright.chromium.launch(
            headless=True,
            args=basic_args,
            timeout=30000
        )
        logger.info("浏览器启动成功")
        
        # 检查浏览器连接
        logger.info(f"浏览器连接状态: {browser.is_connected()}")
        
        # 创建页面
        logger.info("创建新页面...")
        page = await browser.new_page()
        logger.info("页面创建成功")
        
        # 设置超时
        page.set_default_timeout(30000)
        
        # 测试导航到简单页面
        test_url = "https://www.google.com"
        logger.info(f"导航到测试页面: {test_url}")
        
        await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
        logger.info("页面导航成功")
        
        # 获取页面标题
        title = await page.title()
        logger.info(f"页面标题: {title}")
        
        # 获取当前URL
        current_url = page.url
        logger.info(f"当前URL: {current_url}")
        
        logger.info("=== 基础浏览器测试成功 ===")
        return True
        
    except Exception as e:
        logger.error(f"基础浏览器测试失败: {e}")
        return False
        
    finally:
        # 清理资源
        if page:
            try:
                await page.close()
                logger.info("页面已关闭")
            except:
                logger.warning("页面关闭失败")
                
        if browser:
            try:
                await browser.close()
                logger.info("浏览器已关闭")
            except:
                logger.warning("浏览器关闭失败")
                
        if playwright:
            try:
                await playwright.stop()
                logger.info("Playwright已停止")
            except:
                logger.warning("Playwright停止失败")

async def test_google_maps_navigation():
    """测试Google Maps导航"""
    logger.info("=== Google Maps导航测试开始 ===")
    
    playwright = None
    browser = None
    page = None
    
    try:
        # 启动Playwright
        playwright = await async_playwright().start()
        
        # 使用更保守的参数
        conservative_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--single-process'
        ]
        
        # 启动浏览器
        browser = await playwright.chromium.launch(
            headless=True,
            args=conservative_args,
            timeout=30000
        )
        
        logger.info(f"浏览器连接状态: {browser.is_connected()}")
        
        # 创建页面
        page = await browser.new_page()
        page.set_default_timeout(30000)
        
        # 设置用户代理
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 测试URL
        test_url = "https://maps.app.goo.gl/XCLKuyn4vj9qrijE7"
        logger.info(f"导航到Google Maps: {test_url}")
        
        # 尝试导航
        await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
        logger.info("Google Maps导航成功")
        
        # 等待页面稳定
        await page.wait_for_load_state('domcontentloaded', timeout=10000)
        
        # 获取当前URL
        current_url = page.url
        logger.info(f"当前URL: {current_url}")
        
        # 获取页面标题
        title = await page.title()
        logger.info(f"页面标题: {title}")
        
        # 检查是否成功跳转到Google Maps
        if 'google.com/maps' in current_url:
            logger.info("成功跳转到Google Maps")
            
            # 尝试获取页面内容
            content = await page.content()
            logger.info(f"页面内容长度: {len(content)} 字符")
            
            # 检查是否包含商家信息
            if 'Glenny Kebabs' in content or 'Glen Waverley' in content:
                logger.info("页面包含预期的商家信息")
            else:
                logger.warning("页面不包含预期的商家信息")
                
        else:
            logger.warning(f"未成功跳转到Google Maps，当前URL: {current_url}")
        
        logger.info("=== Google Maps导航测试完成 ===")
        return True
        
    except Exception as e:
        logger.error(f"Google Maps导航测试失败: {e}")
        return False
        
    finally:
        # 清理资源
        if page:
            try:
                await page.close()
            except:
                pass
                
        if browser:
            try:
                await browser.close()
            except:
                pass
                
        if playwright:
            try:
                await playwright.stop()
            except:
                pass

async def main():
    """主测试函数"""
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"操作系统: {sys.platform}")
    
    # 测试1: 基础浏览器功能
    basic_success = await test_basic_browser()
    
    if basic_success:
        logger.info("基础浏览器测试通过，继续Google Maps测试")
        # 测试2: Google Maps导航
        maps_success = await test_google_maps_navigation()
        
        if maps_success:
            logger.info("所有测试通过！")
        else:
            logger.error("Google Maps测试失败")
    else:
        logger.error("基础浏览器测试失败，跳过后续测试")

if __name__ == "__main__":
    asyncio.run(main())