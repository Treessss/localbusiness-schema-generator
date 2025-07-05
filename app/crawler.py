"""使用Playwright的网页爬虫，用于提取Google商家信息

该模块实现了一个基于Playwright的异步网页爬虫，专门用于从Google商家页面
提取详细的商家信息，包括名称、地址、电话、营业时间、评分等。

主要功能：
- 单例浏览器实例管理，提高性能
- 异步上下文管理器支持
- 全面的商家信息提取
- 智能选择器策略和备用方案
- 详细的日志记录和错误处理
"""

import asyncio
import platform
import re
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Page, \
    TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from loguru import logger

from .utils import (
    clean_text, parse_rating, parse_review_count, parse_price_range,
    format_phone_number
)


class GoogleBusinessCrawler:
    """Google商家信息爬虫类
    
    使用单例浏览器实例管理，提供高效的商家信息提取功能。
    支持异步操作和上下文管理器模式。
    """

    def __init__(self, headless: bool = True, timeout: int = 60000):
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.playwright = None
        self._is_started = False

    async def _warmup_browser(self):
        """浏览器预热机制
        
        使用最基本的参数先启动浏览器进行预热，
        这可以解决某些环境下复杂参数启动失败的问题。
        """
        logger.info("开始浏览器预热...")
        
        # 最基本的预热参数（与test_browser_basic.py保持一致）
        warmup_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox', 
            '--disable-dev-shm-usage'
        ]
        
        try:
            # 预热浏览器
            warmup_browser = await self.playwright.chromium.launch(
                headless=True,
                args=warmup_args,
                timeout=30000
            )
            
            # 创建测试页面
            warmup_page = await warmup_browser.new_page()
            warmup_page.set_default_timeout(10000)
            
            # 简单导航测试
            await warmup_page.goto('https://www.google.com', 
                                 wait_until='domcontentloaded', 
                                 timeout=10000)
            
            logger.info("浏览器预热成功")
            
            # 清理预热资源
            await warmup_page.close()
            await warmup_browser.close()
            
            return True
            
        except Exception as e:
            logger.warning(f"浏览器预热失败: {e}")
            return False

    async def start(self):
        """启动浏览器实例
        
        初始化Playwright和Chromium浏览器，配置反检测参数。
        如果浏览器已启动则跳过初始化。
        
        Raises:
            Exception: 浏览器启动失败时抛出异常
        """
        if self._is_started:
            logger.info("浏览器实例已经启动")
            return
            
        logger.info("正在启动浏览器实例...")
        self.playwright = await async_playwright().start()
        
        # 执行浏览器预热
        warmup_success = await self._warmup_browser()
        if warmup_success:
            logger.info("浏览器预热完成，继续正常启动")
        else:
            logger.warning("浏览器预热失败，尝试直接启动")
        
        # 检测操作系统并配置相应的浏览器启动参数
        system_name = platform.system().lower()
        logger.info(f"检测到操作系统: {system_name}")
        
        if system_name == 'linux':
            # Linux环境优化配置（与linux_crawler_fix.py保持一致）
            logger.info("使用Linux优化配置")
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-zygote',
                '--single-process',
                '--disable-client-side-phishing-detection',
                '--disable-logging',
                '--disable-crash-reporter',
                '--disable-component-update',
                '--disable-background-networking',
                '--disable-domain-reliability',
                '--disable-features=MediaRouter',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-background-downloads',
                '--disable-add-to-shelf',
                '--disable-office-editing-component-app',
                '--disable-component-extensions-with-background-pages',
                '--disable-features=BlinkGenPropertyTrees',
                '--disable-accelerated-2d-canvas',
                '--disable-accelerated-jpeg-decoding',
                '--disable-accelerated-mjpeg-decode',
                '--disable-accelerated-video-decode',
                '--disable-accelerated-video-encode',
                '--disable-app-list-dismiss-on-blur',
                '--disable-background-mode',
                '--disable-breakpad',
                '--disable-checker-imaging',
                '--disable-component-cloud-policy',
                '--disable-composited-antialiasing',
                '--disable-default-apps',
                '--disable-demo-mode',
                '--disable-device-discovery-notifications',
                '--disable-domain-blocking-for-3d-apis',
                '--disable-features=AudioServiceOutOfProcess',
                '--disable-features=VizDisplayCompositor',
                '--disable-field-trial-config',
                '--disable-file-system',
                '--disable-fine-grained-time-zone-detection',
                '--disable-geolocation',
                '--disable-gl-extensions',
                '--disable-histogram-customizer',
                '--disable-in-process-stack-traces',
                '--disable-infobars',
                '--disable-ipc-flooding-protection',
                '--disable-local-storage',
                '--disable-logging',
                '--disable-login-animations',
                '--disable-new-profile-management',
                '--disable-notifications',
                '--disable-password-generation',
                '--disable-permissions-api',
                '--disable-plugins-discovery',
                '--disable-popup-blocking',
                '--disable-print-preview',
                '--disable-renderer-accessibility',
                '--disable-session-storage',
                '--disable-shared-workers',
                '--disable-speech-api',
                '--disable-sync',
                '--disable-tab-for-desktop-share',
                '--disable-threaded-animation',
                '--disable-threaded-scrolling',
                '--disable-translate',
                '--disable-voice-input',
                '--disable-wake-on-wifi',
                '--disable-web-security',
                '--force-color-profile=srgb',
                '--force-device-scale-factor=1',
                '--hide-scrollbars',
                '--ignore-certificate-errors',
                '--ignore-certificate-errors-spki-list',
                '--ignore-ssl-errors',
                '--mute-audio',
                '--no-default-browser-check',
                '--no-first-run',
                '--no-pings',
                '--no-sandbox',
                '--no-zygote',
                '--single-process',
                '--use-mock-keychain'
            ]
        else:
            # 其他操作系统（Windows, macOS等）的通用配置
            logger.info(f"使用通用配置适配 {system_name} 系统")
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--disable-client-side-phishing-detection',
                '--disable-logging',
                '--disable-crash-reporter',
                '--disable-component-update',
                '--disable-background-networking',
                '--disable-domain-reliability',
                '--disable-features=MediaRouter',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-background-downloads',
                '--disable-add-to-shelf',
                '--disable-office-editing-component-app',
                '--disable-component-extensions-with-background-pages'
            ]
        
        try:
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # 强制无头模式
                args=browser_args
            )
            self._is_started = True
            logger.info("浏览器实例启动成功（无头模式）")
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            # 检查是否是依赖缺失错误
            if "Host system is missing dependencies" in str(e) or "dependencies to run browsers" in str(e):
                logger.error("检测到系统缺少Playwright浏览器依赖")
                logger.error("请运行以下命令安装依赖:")
                logger.error("1. playwright install-deps")
                logger.error("2. playwright install chromium")
                logger.error("或者使用Docker部署以避免依赖问题")
                raise RuntimeError("系统缺少Playwright浏览器依赖。请安装依赖或使用Docker部署。")
            
            # 尝试使用预热时相同的简化配置
            try:
                logger.info("尝试使用预热配置启动浏览器...")
                warmup_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage'
                ]
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=warmup_args,
                    timeout=30000
                )
                self._is_started = True
                logger.info("浏览器实例启动成功（预热配置）")
            except Exception as e2:
                logger.error(f"预热配置启动也失败: {e2}")
                
                # 最后尝试最基本的配置
                try:
                    logger.info("尝试最基本配置启动浏览器...")
                    self.browser = await self.playwright.chromium.launch(
                        headless=True,
                        args=['--no-sandbox']
                    )
                    self._is_started = True
                    logger.info("浏览器实例启动成功（最基本配置）")
                except Exception as e3:
                    logger.error(f"所有配置启动都失败: {e3}")
                    if "Host system is missing dependencies" in str(e3) or "dependencies to run browsers" in str(e3):
                        logger.error("系统缺少Playwright浏览器依赖")
                        logger.error("解决方案:")
                        logger.error("1. 安装依赖: playwright install-deps && playwright install chromium")
                        logger.error("2. 使用Docker部署（推荐）")
                        logger.error("3. 在支持的操作系统上运行")
                        raise RuntimeError("系统缺少Playwright浏览器依赖。请安装依赖或使用Docker部署。")
                    raise Exception(f"无法启动浏览器: {e3}")

    async def stop(self):
        """停止浏览器实例
        
        关闭浏览器和Playwright实例，释放系统资源。
        如果浏览器未启动则跳过关闭操作。
        """
        if not self._is_started:
            logger.info("浏览器实例未启动")
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

    async def __aenter__(self):
        """异步上下文管理器入口
        
        自动启动浏览器实例，支持with语句使用。
        保持向后兼容性。
        
        Returns:
            GoogleBusinessCrawler: 当前实例
        """
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出
        
        自动停止浏览器实例，清理资源。
        保持向后兼容性。
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪信息
        """
        await self.stop()

    async def extract_business_info(self, url: str) -> Dict[str, Any]:
        """从Google商家URL提取完整的商家信息
        
        访问指定URL并提取商家的详细信息，包括名称、地址、电话、
        营业时间、评分、价格范围、网站和图片等。
        
        Args:
            url: Google商家页面URL
            
        Returns:
            Dict[str, Any]: 包含商家信息的字典，包含以下字段：
                - name: 商家名称
                - rating: 评分
                - review_count: 评论数量
                - address: 地址
                - phone: 电话号码
                - opening_hours: 营业时间
                - price_range: 价格范围
                - website: 网站URL
                - business_type: 商家类型
                - images: 图片列表
                - current_url: 重定向后的当前URL
                - original_url: 原始URL
                
        Raises:
            RuntimeError: 浏览器实例未启动
            Exception: 页面加载超时或提取失败
        """
        if not self._is_started or not self.browser:
            raise RuntimeError("浏览器实例未启动，请先调用 start() 方法")

        # 检查浏览器连接状态
        if not self.browser.is_connected():
            logger.warning("浏览器连接已断开，尝试重新启动...")
            await self.stop()
            await self.start()
            if not self.browser or not self.browser.is_connected():
                raise RuntimeError("无法重新建立浏览器连接")

        logger.info(f"开始提取商家信息，URL: {url}")

        page = await self.browser.new_page()

        current_url = url

        try:
            # 设置视口和用户代理以避免检测
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })

            # 使用更保守的导航策略（Linux优化版）
            navigation_success = False
            try:
                logger.info(f"尝试导航到页面，等待条件: networkidle")
                await page.goto(url, 
                               wait_until='networkidle', 
                               timeout=self.timeout)
                navigation_success = True
                logger.info("页面导航成功（networkidle）")
            except PlaywrightTimeoutError:
                logger.warning("networkidle超时，尝试domcontentloaded")
                try:
                    await page.goto(url, 
                                   wait_until='domcontentloaded', 
                                   timeout=self.timeout // 2)
                    navigation_success = True
                    logger.info("页面导航成功（domcontentloaded）")
                except PlaywrightTimeoutError:
                    logger.warning("domcontentloaded也超时，尝试load")
                    try:
                        await page.goto(url, 
                                       wait_until='load', 
                                       timeout=self.timeout // 3)
                        navigation_success = True
                        logger.info("页面导航成功（load）")
                    except PlaywrightTimeoutError:
                        logger.error("所有导航策略都失败")
                        raise Exception("Navigation timeout - all strategies failed")
            
            if not navigation_success:
                raise Exception("Navigation failed")
            
            # 验证页面是否真的加载了
            current_url = page.url
            logger.info(f"当前页面URL: {current_url}")

            # 等待页面稳定并验证加载状态
            try:
                # 检查页面和浏览器连接状态
                if page.is_closed():
                    raise Exception("页面已关闭")
                if not self.browser.is_connected():
                    raise Exception("浏览器连接已断开")
                
                logger.info(page.url)
                
                # 等待页面稳定
                await page.wait_for_load_state('domcontentloaded', timeout=5000)
                logger.info("页面DOM内容已加载")
                
            except PlaywrightTimeoutError:
                logger.warning(f"页面状态检查超时，但继续提取: {current_url}")
            except Exception as e:
                if "closed" in str(e).lower():
                    logger.error(f"页面或浏览器连接已关闭: {e}")
                    raise Exception(f"页面或浏览器连接已关闭: {e}")
                else:
                    logger.warning(f"页面状态检查失败: {e}")

            # 提取商家信息
            business_info = await self._extract_business_data(page)

            # 添加当前URL（重定向后）到商家数据
            business_info['current_url'] = current_url
            business_info['original_url'] = url

            logger.info(
                f"成功提取商家信息: {business_info.get('name', '未知商家')}")
            logger.info(f"重定向后的当前URL: {current_url}")
            return business_info

        except PlaywrightTimeoutError:
            logger.error(f"页面加载超时: {current_url}")
            raise Exception(f"页面加载超时: {current_url}")
        except Exception as e:
            logger.error(f"从URL {current_url} 提取商家信息时出错: {e}")
            raise Exception(f"提取商家信息失败: {str(e)}")
        finally:
            try:
                if page and not page.is_closed():
                    await page.close()
            except Exception as e:
                logger.warning(f"关闭页面时出错: {e}")

    async def _extract_business_data(self, page: Page) -> Dict[str, Any]:
        """从页面提取商家数据
        
        提取包括名称、评分、地址、电话、营业时间、价格范围、
        网站URL、业务类型和图片等完整的商家信息。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            包含商家信息的字典
        """
        logger.info("开始提取商家数据")
        business_info = {}

        try:
            # 检查页面和浏览器连接状态
            if page.is_closed():
                raise Exception("页面已关闭，无法提取数据")
            if not self.browser.is_connected():
                raise Exception("浏览器连接已断开，无法提取数据")
            # 提取商家名称
            logger.info("开始提取商家名称")
            business_info['name'] = await self._extract_business_name(page)
            logger.info(f"商家名称提取完成: {business_info['name']}")

            # 提取评分和评论数
            logger.info("开始提取评分和评论数")
            rating_info = await self._extract_rating_info(page)
            business_info.update(rating_info)
            logger.info(f"评分信息提取完成: {rating_info}")

            # 提取地址
            logger.info("开始提取地址")
            address_result = await self._extract_address(page)
            if isinstance(address_result, dict):
                business_info['address'] = address_result.get('address')
                if address_result.get('extendedAddress'):
                    business_info['extended_address'] = address_result.get('extendedAddress')
                logger.info(
                    f"地址提取完成: {business_info['address']}, 额外地址: {business_info.get('extended_address')}")
            else:
                business_info['address'] = address_result
                logger.info(f"地址提取完成: {business_info['address']}")

            # 提取电话号码
            logger.info("开始提取电话号码")
            business_info['phone'] = await self._extract_phone(page)
            logger.info(f"电话号码提取完成: {business_info['phone']}")

            # 提取营业时间
            logger.info("开始提取营业时间")
            opening_hours = await self._extract_business_hours(page)
            if opening_hours:
                # 格式化为Schema.org OpeningHoursSpecification
                business_info['opening_hours'] = opening_hours
            logger.info(
                f"营业时间提取完成: {business_info.get('opening_hours', business_info.get('opening_hours_text', 'None'))}")

            # 提取价格范围
            logger.info("开始提取价格范围")
            business_info['price_range'] = await self._extract_price_range(page)
            logger.info(f"价格范围提取完成: {business_info['price_range']}")

            # 提取网站URL
            logger.info("开始提取网站URL")
            business_info['website'] = await self._extract_website(page)
            logger.info(f"网站URL提取完成: {business_info['website']}")

            # 提取业务类型/分类
            logger.info("开始提取业务类型")
            business_info['business_type'] = await self._extract_business_type(page)
            logger.info(f"业务类型提取完成: {business_info['business_type']}")

            # 提取图片
            logger.info("开始提取图片")
            business_info['images'] = await self._extract_business_images(page)
            logger.info(
                f"图片提取完成，共{len(business_info['images']) if business_info['images'] else 0}张")

            logger.info("商家数据提取全部完成")

        except Exception as e:
            logger.error(f"提取商家数据时发生错误: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")

        return business_info

    async def _get_page_soup(self, page: Page) -> BeautifulSoup:
        """获取页面HTML并创建BeautifulSoup对象
        
        Args:
            page: Playwright页面对象
            
        Returns:
            BeautifulSoup解析对象
        """
        try:
            # 检查页面和浏览器连接状态
            if page.is_closed():
                raise Exception("页面已关闭，无法获取页面内容")
            if not self.browser.is_connected():
                raise Exception("浏览器连接已断开，无法获取页面内容")
            
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'lxml')
            logger.info("成功创建BeautifulSoup对象")
            return soup
        except Exception as e:
            if "closed" in str(e).lower():
                logger.error(f"页面或浏览器连接问题: {e}")
            else:
                logger.error(f"创建BeautifulSoup对象失败: {e}")
            raise

    async def _extract_business_name(self, page: Page) -> Optional[str]:
        """使用BeautifulSoup提取商家名称
        
        优先使用BeautifulSoup进行解析，失败时回退到Playwright方法。
        使用多个选择器策略确保最大的成功率。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            商家名称字符串，未找到时返回None
        """
        logger.info("开始使用BeautifulSoup提取商家名称")

        try:
            soup = await self._get_page_soup(page)

            # 定义选择器优先级列表
            selectors = [
                'h1',
                'h1[data-attrid="title"]',
                'h1.x3AX1-LfntMc-header-title-title',
                '[data-attrid="title"] h1',
                '[role="main"] h1'
            ]

            for i, selector in enumerate(selectors):
                try:
                    logger.info(f"尝试BeautifulSoup选择器 {i + 1}/{len(selectors)}: {selector}")
                    elements = soup.select(selector)

                    if elements:
                        for element in elements:
                            text = element.get_text(strip=True)
                            if text and len(text) > 0:
                                logger.info(f"成功提取商家名称: {text}")
                                return clean_text(text)
                        logger.info("找到元素但文本为空")
                    else:
                        logger.info("未找到匹配的元素")

                except Exception as e:
                    logger.warning(f"BeautifulSoup选择器 {selector} 失败: {e}")
                    continue

            # 如果所有选择器都失败，尝试备用方案
            logger.info("尝试备用方案：查找所有h1标签")
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                text = h1.get_text(strip=True)
                if text and len(text) > 2:  # 至少3个字符
                    logger.info(f"备用方案成功提取商家名称: {text}")
                    return clean_text(text)

        except Exception as e:
            logger.error(f"BeautifulSoup提取商家名称失败: {e}")
            # 如果BeautifulSoup失败，回退到原有的Playwright方法
            logger.info("回退到Playwright方法")
            return await self._extract_business_name_playwright(page)

        logger.warning("所有方法都未能提取到商家名称")
        return None

    async def _extract_business_name_playwright(self, page: Page) -> Optional[str]:
        """使用Playwright提取商家名称的备用方法
        
        当BeautifulSoup方法失败时使用的备用提取方法。
        使用多个选择器策略确保最大的成功率。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            Optional[str]: 商家名称字符串，未找到时返回None
        """
        selectors = ['h1', 'h1[data-attrid="title"]', '[role="main"] h1']

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return clean_text(text)
            except Exception as e:
                logger.warning(f"Playwright选择器 {selector} 失败: {e}")
                continue

        logger.warning("所有选择器都未能提取到商家名称")
        return None

    async def _extract_rating_info(self, page: Page) -> Dict[str, Any]:
        """提取评分和评论数信息
        
        使用JavaScript在页面中查找评分（1-5分）和评论数量。
        支持多种语言的评论数格式识别。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            Dict[str, Any]: 包含以下字段的字典：
                - rating: 评分（1-5分的浮点数）
                - review_count: 评论数量（整数）
        """
        logger.info("开始提取评分信息")
        rating_info = {}

        # 使用JavaScript查找评分
        try:
            logger.info("正在查找评分")
            rating = await page.evaluate("""
                () => {
                    // 查找包含评分的span元素
                    const spans = document.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent;
                        if (text && /^\d+\.\d+$/.test(text.trim())) {
                            const rating = parseFloat(text.trim());
                            if (rating >= 1 && rating <= 5) {
                                return text.trim();
                            }
                        }
                    }
                    return null;
                }
            """)
            if rating:
                rating_info['rating'] = float(rating)
                logger.info(f"成功提取评分: {rating}")
            else:
                logger.warning("未找到评分")
        except Exception as e:
            logger.error(f"提取评分时出错: {e}")

        # 使用JavaScript查找评论数
        try:
            logger.info("正在查找评论数")
            review_count = await page.evaluate("""
                () => {
                    // 优先查找aria-label属性中包含reviews的元素
                    const ariaElements = document.querySelectorAll('[aria-label*="reviews"], [aria-label*="条评价"], [aria-label*="评价"]');
                    for (const element of ariaElements) {
                        const ariaLabel = element.getAttribute('aria-label');
                        if (ariaLabel) {
                            const match = ariaLabel.match(/(\d{1,3}(?:,\d{3})*)\s*(?:reviews|条评价|评价)/);
                            if (match) {
                                return match[1].replace(/,/g, '');
                            }
                        }
                    }
                    
                    // 备用方案：查找包含评论数的元素，格式如 (3,541)
                    const elements = document.querySelectorAll('span');
                    for (const element of elements) {
                        const text = element.textContent;
                        if (text && text.match(/^\(\d{1,3}(?:,\d{3})*\)$/)) {
                            const match = text.match(/\((\d{1,3}(?:,\d{3})*)\)/);
                            if (match) {
                                return match[1].replace(/,/g, '');
                            }
                        }
                    }
                    return null;
                }
            """)
            if review_count:
                rating_info['review_count'] = int(review_count)
                logger.info(f"成功提取评论数: {review_count}")
            else:
                logger.warning("未找到评论数")
        except Exception as e:
            logger.error(f"提取评论数时出错: {e}")

        logger.info(f"评分信息提取完成: {rating_info}")
        return rating_info

    async def _extract_address(self, page: Page) -> dict[str, str | None] | str | None:
        """提取商家地址信息
        
        提取主地址和扩展地址信息（如所在区域）。
        使用多种选择器策略和地址模式匹配。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            Union[Dict[str, Optional[str]], str, None]: 
                - 字典格式：{'address': 主地址, 'extendedAddress': 扩展地址}
                - 字符串格式：简单地址字符串
                - None: 未找到地址时返回
        """
        logger.info("开始提取地址信息")
        try:
            # 使用JavaScript查找包含地址的元素
            logger.info("正在查找地址")
            # 尝试使用具体的地址选择器
            address_data = await page.evaluate("""
                () => {
                    // 优先查找带有地址标识的按钮或元素
                    const addressSelectors = [
                        'button[data-item-id="address"]',
                        'button[aria-label*="地址"]',
                        'button[aria-label*="Address"]',
                        '.Io6YTe.fontBodyMedium.kR99db.fdkmkc',
                        '[data-attrid="kc:/location:address"]'
                    ];
                    
                    let mainAddress = null;
                    let extendedAddress = null;
                    
                    // 查找主地址
                    for (const selector of addressSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            const text = element.textContent || element.innerText;
                            if (text && text.trim()) {
                                mainAddress = text.trim();
                                break;
                            }
                        }
                    }
                    
                    // 查找额外地址信息 (locatedin)
                    const extendedElement = document.querySelector('button[data-item-id="locatedin"]');
                    if (extendedElement) {
                        const extText = extendedElement.textContent || extendedElement.innerText;
                        if (extText && extText.trim()) {
                            extendedAddress = extText.trim();
                        }
                    }
                    
                    // 如果没有找到主地址，使用备用方法
                    if (!mainAddress) {
                        const elements = document.querySelectorAll('*');
                        for (const element of elements) {
                            const text = element.textContent;
                            if (text && text.length > 10 && text.length < 200) {
                                // 匹配常见地址模式：数字开头，包含街道名称和邮编
                                const addressPattern = /\d+[\s\w\-,.']*\b\d{4}\b/;
                                if (addressPattern.test(text)) {
                                    mainAddress = text.trim();
                                    break;
                                }
                            }
                        }
                    }
                    
                    return {
                        address: mainAddress,
                        extendedAddress: extendedAddress
                    };
                }
            """)
            if address_data and address_data.get('address'):
                main_address = clean_text(address_data['address'])
                extended_address = None
                if address_data.get('extendedAddress'):
                    extended_address = clean_text(address_data['extendedAddress'])
                    logger.info(f"成功提取地址: {main_address}, 额外地址: {extended_address}")
                else:
                    logger.info(f"成功提取地址: {main_address}")

                # 返回结构化地址数据
                return {
                    'address': main_address,
                    'extendedAddress': extended_address
                }
            else:
                logger.warning("未找到地址")
        except Exception as e:
            logger.error(f"提取地址时出错: {e}")

        # 备用选择器
        selectors = [
            '[data-attrid="kc:/location:address"]',
            '.LrzXr',
            '[data-attrid*="address"]',
            'span[data-attrid="kc:/location:address"]'
        ]

        logger.info("尝试备用选择器")
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        logger.info(f"通过选择器 {selector} 找到地址: {text.strip()}")
                        return clean_text(text)
            except Exception:
                continue

        logger.warning("所有方法都未能提取到地址")
        return None

    async def _extract_phone(self, page: Page) -> Optional[str]:
        """提取电话号码
        
        优先查找tel:链接，然后查找页面中的电话号码文本。
        自动格式化电话号码为标准格式。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            Optional[str]: 格式化后的电话号码，未找到时返回None
        """
        logger.info("开始提取电话号码")
        try:
            # 首先尝试查找tel:链接
            logger.info("正在查找tel:链接")
            phone_link = await page.query_selector('a[href^="tel:"]')
            if phone_link:
                href = await phone_link.get_attribute('href')
                if href:
                    phone = href.replace('tel:', '')
                    logger.info(f"通过tel:链接找到电话: {phone}")
                    return format_phone_number(phone)
            else:
                logger.info("未找到tel:链接")
        except Exception as e:
            logger.error(f"查找tel:链接时出错: {e}")

        # 使用JavaScript查找电话号码文本
        try:
            logger.info("正在查找电话号码文本")
            phone = await page.evaluate("""
                () => {
                    // 查找包含电话号码的元素
                    const elements = document.querySelectorAll('*');
                    for (const element of elements) {
                        const text = element.textContent;
                        if (text && /\+61\s*3\s*9574\s*9069/.test(text)) {
                            return text.match(/\+61\s*3\s*9574\s*9069/)[0];
                        }
                    }
                    return null;
                }
            """)
            if phone:
                logger.info(f"通过文本查找到电话: {phone}")
                return format_phone_number(phone)
            else:
                logger.warning("未找到电话号码文本")
        except Exception as e:
            logger.error(f"查找电话号码文本时出错: {e}")

        # 备用选择器
        selectors = [
            '[data-attrid="kc:/location:phone"]',
            'span[data-attrid="kc:/location:phone"]'
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return format_phone_number(text)
            except Exception:
                continue

        return None

    async def _extract_business_hours(self, page: Page) -> List[Dict[str, Any]]:
        """提取营业时间信息
        
        尝试点击营业时间按钮展开详细信息，然后提取每天的营业时间。
        支持多种时间格式和休息日识别。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            营业时间规范列表，符合Schema.org OpeningHoursSpecification格式
        """
        logger.info("开始提取营业时间")
        hours = []

        try:
            # 首先尝试点击营业时间按钮展开详细信息
            logger.info("尝试点击营业时间按钮")
            try:
                # 查找营业时间按钮并点击
                hours_button = await page.query_selector('[jsaction*="pane.openhours"]')
                if not hours_button:
                    hours_button = await page.query_selector('.OMl5r.hH0dDd.jBYmhd')
                if not hours_button:
                    hours_button = await page.query_selector('[aria-label*="营业时间"]')

                if hours_button:
                    await hours_button.click()
                    logger.info("成功点击营业时间按钮")
                    # 等待展开的内容加载
                    await page.wait_for_timeout(1000)
                else:
                    logger.warning("未找到营业时间按钮")
            except Exception as e:
                logger.warning(f"点击营业时间按钮失败: {e}")

            # 提取详细的营业时间信息
            logger.info("正在提取营业时间详情")
            hours_data = await page.evaluate("""
                () => {
                    const hoursData = [];
                    
                    // 查找营业时间表格
                    const tableSelectors = [
                        '.t39EBf.GUrTXd table.eK4R0e',
                        '.t39EBf table',
                        'table.eK4R0e',
                        '[data-attrid="kc:/hours"] table',
                        '.OqCZI table',
                        '.lo7U6b table'
                    ];
                    
                    let table = null;
                    for (const selector of tableSelectors) {
                        table = document.querySelector(selector);
                        if (table) break;
                    }
                    
                    if (table) {
                        // 查找表格中的每一行
                        const rows = table.querySelectorAll('tr.y0skZc, tr');
                        
                        for (const row of rows) {
                            // 查找星期几的单元格
                            const dayCell = row.querySelector('.ylH6lf div, td:first-child div, td:first-child');
                            // 查找时间的单元格容器
                            const timeContainer = row.querySelector('.mxowUb, td:nth-child(2)');
                            
                            if (dayCell && timeContainer) {
                                const dayText = dayCell.textContent?.trim();
                                
                                // 查找所有时间段（支持多个li元素）
                                const timeElements = timeContainer.querySelectorAll('.G8aQO, li');
                                
                                if (timeElements.length > 0) {
                                    // 处理多个时间段
                                    let lastPeriod = null; // 记录上一个时间段的AM/PM
                                    
                                    for (const timeElement of timeElements) {
                                        const timeText = timeElement.textContent?.trim();
                                
                                        if (dayText && timeText) {
                                             // 解析时间范围 - 支持24小时制和AM/PM制（包括混合格式）
                                              const timeMatch = timeText.match(/(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)\s*[–-]\s*(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)/i);
                                             
                                             if (timeMatch) {
                                                 let opens = timeMatch[1].trim();
                                                 let closes = timeMatch[2].trim();
                                                 
                                                 // 检查开始时间是否缺少AM/PM
                                                 if (!/[AP]M/i.test(opens) && lastPeriod) {
                                                     // 如果开始时间没有AM/PM，且有上一个时间段的信息
                                                     const hourMatch = opens.match(/^(\d{1,2})/);
                                                     if (hourMatch) {
                                                         const hour = parseInt(hourMatch[1]);
                                                         // 如果小时数较小(1-11)且上一个时间段是PM，则很可能也是PM
                                                         if (hour >= 1 && hour <= 11 && lastPeriod === 'PM') {
                                                             opens += ' PM';
                                                         } else if (hour >= 1 && hour <= 11 && lastPeriod === 'AM') {
                                                             opens += ' AM';
                                                         }
                                                     }
                                                 }
                                                 
                                                 // 检查结束时间是否缺少AM/PM
                                                 if (!/[AP]M/i.test(closes)) {
                                                     // 如果结束时间没有AM/PM，根据开始时间推断
                                                     const opensHasPM = /PM/i.test(opens);
                                                     const closesHourMatch = closes.match(/^(\d{1,2})/);
                                                     if (closesHourMatch) {
                                                         const closesHour = parseInt(closesHourMatch[1]);
                                                         // 如果开始时间是PM，结束时间通常也是PM
                                                         if (opensHasPM) {
                                                             closes += ' PM';
                                                         } else {
                                                             // 如果开始时间是AM，根据小时数判断
                                                             if (closesHour >= 1 && closesHour <= 11) {
                                                                 closes += ' PM'; // 通常营业到下午
                                                             } else {
                                                                 closes += ' AM';
                                                             }
                                                         }
                                                     }
                                                 }
                                                 
                                                 // 记录当前时间段的period用于下一个时间段
                                                 const periodMatch = closes.match(/([AP]M)/i);
                                                 if (periodMatch) {
                                                     lastPeriod = periodMatch[1].toUpperCase();
                                                 }
                                                 
                                                 hoursData.push({
                                                     day: dayText,
                                                     opens: opens,
                                                     closes: closes,
                                                     raw: `${dayText} ${timeText}`
                                                 });
                                             } else if (timeText.includes('休息') || timeText.includes('关闭') || timeText.includes('暂停营业') || 
                                                       timeText.includes('不营业') || timeText.includes('停业') || timeText.includes('闭店') ||
                                                       timeText.toLowerCase().includes('closed') || timeText.toLowerCase().includes('休') ||
                                                       timeText.toLowerCase().includes('close') || timeText.toLowerCase().includes('休息日')) {
                                                 hoursData.push({
                                                     day: dayText,
                                                     opens: null,
                                                     closes: null,
                                                     raw: `${dayText} ${timeText}`,
                                                     closed: true
                                                 });
                                             }
                                         }
                                    }
                                } else {
                                    // 如果没有找到.G8aQO或li元素，尝试直接从容器获取文本
                                    const timeText = timeContainer.textContent?.trim();
                                    if (dayText && timeText) {
                                        // 解析时间范围
                                        const timeMatch = timeText.match(/(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)\s*[–-]\s*(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)/i);
                                        
                                        if (timeMatch) {
                                            hoursData.push({
                                                day: dayText,
                                                opens: timeMatch[1].trim(),
                                                closes: timeMatch[2].trim(),
                                                raw: `${dayText} ${timeText}`
                                            });
                                        } else if (timeText.includes('休息') || timeText.includes('关闭') || timeText.includes('暂停营业') || 
                                                  timeText.includes('不营业') || timeText.includes('停业') || timeText.includes('闭店') ||
                                                  timeText.toLowerCase().includes('closed') || timeText.toLowerCase().includes('休') ||
                                                  timeText.toLowerCase().includes('close') || timeText.toLowerCase().includes('休息日')) {
                                            hoursData.push({
                                                day: dayText,
                                                opens: null,
                                                closes: null,
                                                raw: `${dayText} ${timeText}`,
                                                closed: true
                                            });
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // 如果表格解析失败，尝试其他选择器
                    if (hoursData.length === 0) {
                        const hoursSelectors = [
                            '[data-attrid="kc:/hours"]',
                            '.t39EBf.GUrTXd',
                            '.OqCZI',
                            '.lo7U6b',
                            '[role="table"]'
                        ];
                        
                        let hoursContainer = null;
                        for (const selector of hoursSelectors) {
                            hoursContainer = document.querySelector(selector);
                            if (hoursContainer) break;
                        }
                        
                        if (hoursContainer) {
                            // 查找每一行的营业时间
                            const rows = hoursContainer.querySelectorAll('[role="row"], .lo7U6b > div, .OqCZI > div, div');
                            
                            for (const row of rows) {
                                const text = row.textContent || row.innerText;
                                if (text && text.trim()) {
                                    // 解析日期和时间
                                    const dayMatch = text.match(/(星期[一二三四五六日]|周[一二三四五六日]|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)/i);
                                    const timeMatch = text.match(/(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)\s*[–-]\s*(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)|休息|关闭|暂停营业|不营业|停业|闭店|休息日|Closed|Close/i);
                                    
                                    if (dayMatch) {
                                         const dayText = dayMatch[1];
                                         let opens = null;
                                         let closes = null;
                                         
                                         // 检查是否为休息日
                                         const isClosedDay = text.includes('休息') || text.includes('关闭') || text.includes('暂停营业') ||
                                                           text.includes('不营业') || text.includes('停业') || text.includes('闭店') ||
                                                           text.includes('休息日') || text.toLowerCase().includes('closed') ||
                                                           text.toLowerCase().includes('close');
                                         
                                         if (isClosedDay) {
                                             hoursData.push({
                                                 day: dayText,
                                                 opens: null,
                                                 closes: null,
                                                 raw: text.trim(),
                                                 closed: true
                                             });
                                         } else {
                                             // 重新匹配时间范围以获取开始和结束时间
                                             const timeRangeMatch = text.match(/(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)\s*[–-]\s*(\d{1,2}(?::\d{2})?(?:\s*[AP]M)?)/i);
                                             
                                             if (timeRangeMatch) {
                                                 opens = timeRangeMatch[1].trim();
                                                 closes = timeRangeMatch[2].trim();
                                             }
                                             
                                             hoursData.push({
                                                 day: dayText,
                                                 opens: opens,
                                                 closes: closes,
                                                 raw: text.trim()
                                             });
                                         }
                                     }
                                }
                            }
                        }
                    }
                    
                    // 如果仍然没有找到详细信息，尝试从简单的营业时间文本中提取
                    if (hoursData.length === 0) {
                        const elements = document.querySelectorAll('*');
                        for (const element of elements) {
                            const text = element.textContent;
                            if (text && (text.includes('营业中') || text.includes('Open') || text.includes('结束营业'))) {
                                const timeMatch = text.match(/(\d{1,2}:\d{2})\s*结束营业/);
                                if (timeMatch) {
                                    hoursData.push({
                                        raw: text.trim(),
                                        current_status: text.includes('营业中') ? 'open' : 'closed',
                                        closes_at: timeMatch[1]
                                    });
                                    break;
                                }
                            }
                        }
                    }
                    
                    return hoursData;
                }
            """)

            if hours_data and len(hours_data) > 0:
                logger.info(f"成功提取营业时间: {len(hours_data)} 条记录")
                # 转换为Schema.org格式
                formatted_hours = self._format_opening_hours(hours_data)
                return formatted_hours
            else:
                logger.warning("未找到营业时间详情")

        except Exception as e:
            logger.error(f"提取营业时间时出错: {e}")

        logger.info(f"营业时间提取完成，找到 {len(hours)} 条记录")
        return hours

    def _format_opening_hours(self, hours_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将营业时间数据格式化为Schema.org OpeningHoursSpecification格式
        
        根据Schema.org规范，将具有相同开放和关闭时间的日期合并到一个
        OpeningHoursSpecification对象中，提高数据的结构化程度。
        
        Args:
            hours_data: 原始营业时间数据列表
            
        Returns:
            格式化后的营业时间规范列表
        """
        logger.info("开始格式化营业时间数据")

        # 中文星期到英文的映射
        day_mapping = {
            '星期一': 'Monday', '周一': 'Monday', 'Mon': 'Monday',
            '星期二': 'Tuesday', '周二': 'Tuesday', 'Tue': 'Tuesday',
            '星期三': 'Wednesday', '周三': 'Wednesday', 'Wed': 'Wednesday',
            '星期四': 'Thursday', '周四': 'Thursday', 'Thu': 'Thursday',
            '星期五': 'Friday', '周五': 'Friday', 'Fri': 'Friday',
            '星期六': 'Saturday', '周六': 'Saturday', 'Sat': 'Saturday',
            '星期日': 'Sunday', '周日': 'Sunday', 'Sun': 'Sunday'
        }

        # 用于合并相同时间段的字典，key为(opens, closes)，value为日期列表
        time_groups = {}

        for hour_data in hours_data:
            # 跳过休息日（closed为true的日期）
            if hour_data.get('closed', False):
                logger.info(f"跳过休息日: {hour_data.get('day', 'Unknown')}")
                continue

            if 'day' in hour_data and hour_data['opens'] and hour_data['closes']:
                day_chinese = hour_data['day']
                day_english = day_mapping.get(day_chinese, day_chinese)

                opens = self._convert_to_24h_format(hour_data['opens'])
                closes = self._convert_to_24h_format(hour_data['closes'])

                # 使用(opens, closes)作为key来分组
                time_key = (opens, closes)
                if time_key not in time_groups:
                    time_groups[time_key] = []
                time_groups[time_key].append(day_english)

                logger.info(f"处理营业时间: {day_english} {opens}-{closes}")

        # 生成合并后的OpeningHoursSpecification对象
        formatted_hours = []
        for (opens, closes), days in time_groups.items():
            opening_hours_spec = {
                '@type': 'OpeningHoursSpecification',
                'dayOfWeek': days if len(days) > 1 else days[0],  # 多天用数组，单天用字符串
                'opens': opens,
                'closes': closes
            }
            formatted_hours.append(opening_hours_spec)

            logger.info(f"添加合并的营业时间规范: {days} {opens}-{closes}")

        logger.info(f"格式化完成，生成 {len(formatted_hours)} 个营业时间规范")
        return formatted_hours

    def _convert_to_24h_format(self, time_str: str) -> str:
        """将时间字符串转换为24小时格式 (hh:mm:ss)
        
        支持AM/PM格式、24小时制格式和纯小时格式的转换。
        
        Args:
            time_str: 输入的时间字符串
            
        Returns:
            24小时制格式的时间字符串 (hh:mm:ss)
        """
        if not time_str:
            return time_str

        time_str = time_str.strip()

        # 如果已经是hh:mm:ss格式，直接返回
        if re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):
            return time_str

        # 处理AM/PM格式
        am_pm_match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*([AP]M)$', time_str, re.IGNORECASE)
        if am_pm_match:
            hour = int(am_pm_match.group(1))
            minute = int(am_pm_match.group(2)) if am_pm_match.group(2) else 0
            period = am_pm_match.group(3).upper()

            # 转换为24小时制
            if period == 'AM':
                if hour == 12:
                    hour = 0
            else:  # PM
                if hour != 12:
                    hour += 12

            return f"{hour:02d}:{minute:02d}:00"

        # 处理24小时制格式 (hh:mm)
        time_24h_match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
        if time_24h_match:
            hour = int(time_24h_match.group(1))
            minute = int(time_24h_match.group(2))
            return f"{hour:02d}:{minute:02d}:00"

        # 处理只有小时的格式
        hour_only_match = re.match(r'^(\d{1,2})$', time_str)
        if hour_only_match:
            hour = int(hour_only_match.group(1))
            return f"{hour:02d}:00:00"

        # 如果无法解析，返回原始字符串
        logger.warning(f"无法解析时间格式: {time_str}")
        return time_str

    async def _extract_price_range(self, page: Page) -> Optional[str]:
        """提取价格范围信息
        
        查找价格等级符号（$$, $$$等）或具体价格范围。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            价格范围字符串，未找到时返回None
        """
        logger.info("开始提取价格范围")
        try:
            # 使用JavaScript查找价格范围
            logger.info("正在查找价格范围")
            price_range = await page.evaluate("""
                () => {
                    // 查找价格相关的元素
                    const elements = document.querySelectorAll('*');
                    for (const element of elements) {
                        const text = element.textContent;
                        if (text) {
                            // 优先匹配价格等级符号（$$, $$$, $$$$）
                            const priceLevelMatch = text.match(/\$\$+/);
                            if (priceLevelMatch && priceLevelMatch[0].length >= 2 && priceLevelMatch[0].length <= 4) {
                                return priceLevelMatch[0];
                            }
                            
                            // 匹配具体价格范围，支持各种货币符号和分隔符
                            const priceRangeMatch = text.match(/([A-Z]*\$|¥|€|£)\s*(\d+)[–-](\d+)/);
                            if (priceRangeMatch) {
                                // 标准化格式：移除货币前缀，只保留基本货币符号
                                const currency = priceRangeMatch[1];
                                const minPrice = priceRangeMatch[2];
                                const maxPrice = priceRangeMatch[3];
                                return `${currency}${minPrice}-${maxPrice}`;
                            }
                            
                            // 匹配单个价格（如 $25, A$30）并标准化
                            const singlePriceMatch = text.match(/([A-Z]*\$|¥|€|£)\s*(\d+)/);
                            if (singlePriceMatch && text.trim().length < 20) {
                                // 标准化格式：移除货币前缀
                                const currency = singlePriceMatch[1].replace(/^[A-Z]+/, '').replace(/\$/, '$');
                                const price = singlePriceMatch[2];
                                return `${currency}${price}`;
                            }
                        }
                    }
                    return null;
                }
            """)
            if price_range:
                logger.info(f"成功提取价格范围: {price_range}")
                return price_range
            else:
                logger.warning("未找到价格范围")
        except Exception as e:
            logger.error(f"提取价格范围时出错: {e}")

        # 备用选择器
        selectors = [
            '[data-attrid*="price"]',
            '.YrbPuc',
            'span[aria-label*="Price"]'
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    price_range = parse_price_range(text)
                    if price_range:
                        return price_range
            except Exception:
                continue

        return None

    async def _extract_website(self, page: Page) -> Optional[str]:
        """提取商家网站URL
        
        查找商家官方网站链接，过滤掉Google相关的链接。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            网站URL，未找到时返回None
        """
        logger.info("开始提取网站URL")
        try:
            # 使用JavaScript查找网站链接
            logger.info("正在查找网站链接")
            website = await page.evaluate("""
                () => {
                    // 通用网站提取逻辑
                    
                    // 1. 查找带有网站相关属性的链接
                    const websiteSelectors = [
                        'a[data-item-id="authority"]',  // Google Maps 网站链接
                        'a[aria-label*="Website"]',     // 包含Website的aria-label
                        'a[data-tooltip="Open website"]', // 网站工具提示
                        'a[href^="http"][class*="CsEnBe"]', // Google Maps特定的网站链接类
                        'a[jsaction*="wfvdle32"]'       // Google Maps网站链接的jsaction
                    ];
                    
                    for (const selector of websiteSelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const element of elements) {
                            const href = element.href;
                            if (href && href.startsWith('http') && !href.includes('google.com') && !href.includes('maps.google')) {
                                return href;
                            }
                        }
                    }
                    
                    // 2. 查找包含网站URL文本的元素
                    const textElements = document.querySelectorAll('div.Io6YTe, span, div');
                    for (const element of textElements) {
                        const text = element.textContent?.trim();
                        if (text && text.match(/^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/)) {
                            // 匹配域名格式的文本
                            return text.startsWith('http') ? text : `https://${text}`;
                        }
                    }
                    
                    // 3. 查找所有外部链接作为备选
                    const allLinks = document.querySelectorAll('a[href^="http"]');
                    for (const link of allLinks) {
                        const href = link.href;
                        if (href && 
                            !href.includes('google.com') && 
                            !href.includes('maps.google') && 
                            !href.includes('gstatic.com') && 
                            !href.includes('googleapis.com')) {
                            return href;
                        }
                    }
                    
                    return null;
                }
            """)
            if website:
                logger.info(f"成功提取网站URL: {website}")
                return website
            else:
                logger.warning("未找到网站URL")
        except Exception as e:
            logger.error(f"提取网站URL时出错: {e}")

        # 备用选择器
        selectors = [
            'a[data-attrid="kc:/location:website"]',
            'a[href^="http"][data-attrid*="website"]'
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    href = await element.get_attribute('href')
                    if href and href.startswith('http'):
                        return href
            except Exception:
                continue

        return None

    async def _extract_business_type(self, page: Page) -> Optional[str]:
        """提取商家类型/类别信息
        
        查找商家的业务类型或类别标签。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            商家类型字符串，未找到时返回None
        """
        logger.info("开始提取业务类型")
        try:
            # 使用JavaScript查找业务类型
            logger.info("正在查找业务类型")
            business_type = await page.evaluate("""
                () => {
                    // 通用商家类型提取逻辑
                    
                    // 1. 查找带有category相关属性的按钮
                    const categorySelectors = [
                        'button[jsaction*="category"]',     // Google Maps 商家类型按钮
                        'button.DkEaL',                     // Google Maps特定的类型按钮类
                        'span[jsaction*="category"] button', // 嵌套在span中的类型按钮
                        '[data-value*="category"]',         // 包含category的data-value
                        'button[aria-label*="category"]'    // 包含category的aria-label
                    ];
                    
                    for (const selector of categorySelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const element of elements) {
                            const text = element.textContent?.trim();
                            if (text && text.length > 0 && text.length < 50) {
                                // 过滤掉过长或过短的文本
                                return text;
                            }
                        }
                    }
                    
                    // 2. 查找包含在fontBodyMedium类中的按钮
                    const mediumTextButtons = document.querySelectorAll('.fontBodyMedium button');
                    for (const button of mediumTextButtons) {
                        const text = button.textContent?.trim();
                        if (text && text.length > 0 && text.length < 50) {
                            return text;
                        }
                    }
                    
                    // 3. 查找所有可能的商家类型按钮（备选方案）
                    const allButtons = document.querySelectorAll('button');
                    for (const button of allButtons) {
                        const text = button.textContent?.trim();
                        const jsaction = button.getAttribute('jsaction');
                        
                        // 检查是否包含类型相关的jsaction或文本特征
                        if (text && text.length > 2 && text.length < 30 && 
                            (jsaction?.includes('category') || 
                             text.match(/^[A-Za-z\s&-]+$/) || // 英文类型
                             text.match(/^[\u4e00-\u9fa5\s]+$/))) { // 中文类型
                            return text;
                        }
                    }
                    
                    return null;
                }
            """)
            if business_type:
                logger.info(f"成功提取业务类型: {business_type}")
                return business_type
            else:
                logger.warning("未找到业务类型")
        except Exception as e:
            logger.error(f"提取业务类型时出错: {e}")

        # 备用选择器
        selectors = [
            '[data-attrid="kc:/location:category"]',
            '.YhemCb',
            'span[data-attrid="kc:/location:category"]'
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return clean_text(text)
            except Exception:
                continue

        return None

    async def _extract_business_images(self, page: Page) -> List[str]:
        """提取商家图片
        
        查找商家的封面图片和其他相关图片。
        
        Args:
            page: Playwright页面对象
            
        Returns:
            图片URL列表
        """
        logger.info("开始查找图片元素")
        images = []

        try:
            # Look for cover image in the business listing
            logger.info("正在查找封面图片")
            # 查找封面图片 - 在ZKCDEc div中的主要图片
            cover_img = await page.query_selector(
                '.ZKCDEc .RZ66Rb button img[src*="googleusercontent"]')

            if cover_img:
                src = await cover_img.get_attribute('src')
                if src and 'googleusercontent' in src:
                    images.append(src)
                    logger.info(f"成功添加封面图片: {src[:100]}...")
            else:
                # 备用选择器：查找第一个googleusercontent图片
                logger.info("未找到封面图片，尝试备用选择器")
                first_img = await page.query_selector('img[src*="googleusercontent"]')
                if first_img:
                    src = await first_img.get_attribute('src')
                    if src and 'googleusercontent' in src:
                        images.append(src)
                        logger.info(f"成功添加备用图片: {src[:100]}...")

            logger.info(f"图片提取完成，共获取{len(images)}张图片")
        except Exception as e:
            logger.error(f"提取图片时发生错误: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")

        return images
