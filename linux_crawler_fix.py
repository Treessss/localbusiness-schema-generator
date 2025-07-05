#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux环境下Playwright爬虫优化脚本

针对Linux服务器环境下Playwright可能出现的卡住问题提供解决方案。
主要解决以下问题：
1. 页面导航超时
2. 浏览器启动参数不适配Linux
3. 系统资源限制
4. 网络连接问题

使用方法：
1. 直接运行测试: python linux_crawler_fix.py
2. 导入使用: from linux_crawler_fix import LinuxOptimizedCrawler
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, PlaywrightTimeoutError
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LinuxOptimizedCrawler:
    """针对Linux环境优化的爬虫类
    
    专门为Linux服务器环境设计，解决常见的卡住和超时问题。
    """
    
    def __init__(self, timeout: int = 30000):
        """初始化爬虫
        
        Args:
            timeout: 页面加载超时时间（毫秒），Linux环境建议使用较短超时
        """
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.playwright = None
        self._is_started = False
        
    async def start(self):
        """启动浏览器实例（Linux优化版）"""
        if self._is_started:
            logger.info("浏览器实例已经启动")
            return
            
        logger.info("正在启动浏览器实例（Linux优化模式）...")
        self.playwright = await async_playwright().start()
        
        # Linux环境优化的浏览器启动参数
        linux_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-features=VizDisplayCompositor',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--mute-audio',
            '--no-zygote',
            '--single-process',
            '--memory-pressure-off',
            '--max_old_space_size=4096',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-blink-features=AutomationControlled',
            '--disable-ipc-flooding-protection',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-images',  # 禁用图片加载以提高速度
            '--disable-javascript',  # 禁用JS以避免复杂交互
        ]
        
        try:
            # 尝试启动浏览器
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=linux_args,
                timeout=30000  # 浏览器启动超时30秒
            )
            self._is_started = True
            logger.info("浏览器实例启动成功（Linux优化模式）")
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            
            # 尝试最小化配置
            try:
                logger.info("尝试最小化配置启动浏览器...")
                minimal_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process'
                ]
                
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=minimal_args,
                    timeout=20000
                )
                self._is_started = True
                logger.info("浏览器实例启动成功（最小化配置）")
                
            except Exception as e2:
                logger.error(f"最小化配置启动也失败: {e2}")
                await self._diagnose_system()
                raise Exception(f"无法启动浏览器: {e2}")
    
    async def _diagnose_system(self):
        """诊断系统环境"""
        logger.info("=== 系统环境诊断 ===")
        logger.info(f"操作系统: {sys.platform}")
        logger.info(f"Python版本: {sys.version}")
        
        # 检查内存
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemAvailable' in line:
                        logger.info(f"可用内存: {line.strip()}")
                        break
        except:
            logger.warning("无法读取内存信息")
        
        # 检查/dev/shm
        try:
            shm_stat = os.statvfs('/dev/shm')
            shm_size = shm_stat.f_bavail * shm_stat.f_frsize / 1024 / 1024
            logger.info(f"/dev/shm 可用空间: {shm_size:.2f} MB")
        except:
            logger.warning("无法检查/dev/shm")
            
        # 检查Playwright安装
        try:
            import subprocess
            result = subprocess.run(['playwright', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            logger.info(f"Playwright版本: {result.stdout.strip()}")
        except:
            logger.warning("Playwright命令不可用")
    
    async def stop(self):
        """停止浏览器实例"""
        if not self._is_started:
            return
            
        logger.info("正在停止浏览器实例...")
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self._is_started = False
        logger.info("浏览器实例已停止")
    
    async def extract_business_info_safe(self, url: str) -> Dict[str, Any]:
        """安全的商家信息提取（Linux优化版）
        
        Args:
            url: Google商家页面URL
            
        Returns:
            包含商家信息的字典
        """
        if not self._is_started or not self.browser:
            raise RuntimeError("浏览器实例未启动")
        
        logger.info(f"开始提取商家信息（Linux优化模式），URL: {url}")
        
        page = None
        try:
            page = await self.browser.new_page()
            
            # 设置较短的超时时间
            page.set_default_timeout(self.timeout)
            
            # 设置视口
            await page.set_viewport_size({"width": 1280, "height": 720})
            
            # 设置简化的用户代理
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            logger.info(f"开始导航到URL: {url}")
            
            # 使用较短超时进行导航
            try:
                await page.goto(url, 
                               wait_until='domcontentloaded', 
                               timeout=self.timeout)
                logger.info("页面导航成功")
            except PlaywrightTimeoutError:
                logger.warning("页面导航超时，尝试继续处理")
                # 即使超时也尝试提取信息
            
            # 快速检查页面是否加载
            try:
                await page.wait_for_selector('body', timeout=5000)
                logger.info("页面body元素已加载")
            except PlaywrightTimeoutError:
                logger.warning("页面body元素加载超时")
            
            # 提取基本信息
            business_info = await self._extract_basic_info(page)
            
            # 添加URL信息
            business_info['current_url'] = page.url
            business_info['original_url'] = url
            
            logger.info(f"成功提取商家信息: {business_info.get('name', '未知商家')}")
            return business_info
            
        except Exception as e:
            logger.error(f"提取商家信息时出错: {e}")
            return {
                'name': None,
                'error': str(e),
                'original_url': url,
                'current_url': page.url if page else None
            }
        finally:
            if page:
                await page.close()
    
    async def _extract_basic_info(self, page: Page) -> Dict[str, Any]:
        """提取基本商家信息
        
        Args:
            page: Playwright页面对象
            
        Returns:
            包含基本商家信息的字典
        """
        logger.info("开始提取基本商家信息")
        business_info = {}
        
        try:
            # 获取页面HTML
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取商家名称
            name = None
            name_selectors = ['h1', '[data-attrid="title"] h1', '[role="main"] h1']
            
            for selector in name_selectors:
                elements = soup.select(selector)
                if elements:
                    name = elements[0].get_text(strip=True)
                    if name:
                        break
            
            business_info['name'] = name
            logger.info(f"商家名称: {name}")
            
            # 提取评分
            rating = None
            rating_selectors = [
                '[data-value]',
                '.google-symbols',
                '[role="img"][aria-label*="stars"]'
            ]
            
            for selector in rating_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and ('.' in text or text.replace('.', '').isdigit()):
                        try:
                            rating = float(text.split()[0])
                            break
                        except:
                            continue
                if rating:
                    break
            
            business_info['rating'] = rating
            logger.info(f"评分: {rating}")
            
            # 提取地址（简化版）
            address = None
            address_selectors = [
                '[data-item-id="address"]',
                '[data-attrid="kc:/location/location:address"]',
                'span[jstcache*="address"]'
            ]
            
            for selector in address_selectors:
                elements = soup.select(selector)
                if elements:
                    address = elements[0].get_text(strip=True)
                    if address:
                        break
            
            business_info['address'] = address
            logger.info(f"地址: {address}")
            
        except Exception as e:
            logger.error(f"提取基本信息时出错: {e}")
        
        return business_info
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


async def test_linux_crawler():
    """测试Linux优化爬虫"""
    test_url = "https://maps.app.goo.gl/XCLKuyn4vj9qrijE7"
    
    logger.info("=== Linux环境爬虫测试开始 ===")
    
    async with LinuxOptimizedCrawler(timeout=20000) as crawler:
        try:
            result = await crawler.extract_business_info_safe(test_url)
            logger.info("=== 测试结果 ===")
            for key, value in result.items():
                logger.info(f"{key}: {value}")
        except Exception as e:
            logger.error(f"测试失败: {e}")
    
    logger.info("=== Linux环境爬虫测试结束 ===")


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(test_linux_crawler())