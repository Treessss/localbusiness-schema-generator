#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux环境Playwright问题诊断和修复脚本

自动检测Linux环境下可能导致Playwright卡住的问题并提供解决方案。

使用方法:
    python diagnose_linux.py

检查项目:
1. 系统依赖
2. 内存和存储
3. Playwright安装
4. 浏览器可用性
5. 网络连接
6. 权限问题
"""

import asyncio
import logging
import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LinuxDiagnostic:
    """Linux环境诊断类"""
    
    def __init__(self):
        self.issues = []
        self.recommendations = []
        
    def add_issue(self, issue: str, severity: str = "WARNING"):
        """添加问题"""
        self.issues.append({"issue": issue, "severity": severity})
        
    def add_recommendation(self, recommendation: str):
        """添加建议"""
        self.recommendations.append(recommendation)
    
    async def run_full_diagnosis(self):
        """运行完整诊断"""
        logger.info("=== Linux环境Playwright诊断开始 ===")
        
        # 基本系统信息
        await self.check_system_info()
        
        # 检查系统依赖
        await self.check_system_dependencies()
        
        # 检查内存和存储
        await self.check_memory_and_storage()
        
        # 检查Playwright安装
        await self.check_playwright_installation()
        
        # 检查浏览器
        await self.check_browser_availability()
        
        # 检查网络
        await self.check_network_connectivity()
        
        # 检查权限
        await self.check_permissions()
        
        # 测试浏览器启动
        await self.test_browser_launch()
        
        # 生成报告
        self.generate_report()
        
        logger.info("=== Linux环境Playwright诊断结束 ===")
    
    async def check_system_info(self):
        """检查系统基本信息"""
        logger.info("检查系统基本信息...")
        
        try:
            logger.info(f"操作系统: {platform.system()} {platform.release()}")
            logger.info(f"架构: {platform.machine()}")
            logger.info(f"Python版本: {sys.version}")
            logger.info(f"当前用户: {os.getenv('USER', 'unknown')}")
            
            # 检查是否在容器中运行
            if os.path.exists('/.dockerenv'):
                logger.info("检测到Docker容器环境")
                self.add_recommendation("在Docker环境中，建议使用官方Playwright Docker镜像")
            
            # 检查是否有显示服务器
            display = os.getenv('DISPLAY')
            if not display:
                logger.info("未检测到DISPLAY环境变量（正常，使用无头模式）")
            else:
                logger.info(f"DISPLAY环境变量: {display}")
                
        except Exception as e:
            self.add_issue(f"获取系统信息失败: {e}", "ERROR")
    
    async def check_system_dependencies(self):
        """检查系统依赖"""
        logger.info("检查系统依赖...")
        
        # 检查必要的系统库
        required_libs = [
            'libnss3',
            'libatk-bridge2.0-0',
            'libdrm2',
            'libxcomposite1',
            'libxdamage1',
            'libxrandr2',
            'libgbm1',
            'libxss1',
            'libasound2'
        ]
        
        missing_libs = []
        for lib in required_libs:
            try:
                result = subprocess.run(
                    ['dpkg', '-l', lib],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    missing_libs.append(lib)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # 如果dpkg不可用，跳过检查
                break
        
        if missing_libs:
            self.add_issue(f"缺少系统依赖: {', '.join(missing_libs)}", "ERROR")
            self.add_recommendation("运行: sudo apt-get install -y " + ' '.join(missing_libs))
        else:
            logger.info("系统依赖检查通过")
    
    async def check_memory_and_storage(self):
        """检查内存和存储"""
        logger.info("检查内存和存储...")
        
        try:
            # 检查内存
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                
            for line in meminfo.split('\n'):
                if 'MemAvailable:' in line:
                    mem_kb = int(line.split()[1])
                    mem_mb = mem_kb / 1024
                    logger.info(f"可用内存: {mem_mb:.0f} MB")
                    
                    if mem_mb < 512:
                        self.add_issue(f"可用内存不足: {mem_mb:.0f} MB", "ERROR")
                        self.add_recommendation("建议至少512MB可用内存")
                    elif mem_mb < 1024:
                        self.add_issue(f"可用内存较少: {mem_mb:.0f} MB", "WARNING")
                        self.add_recommendation("建议增加内存或关闭其他程序")
                    break
            
            # 检查/dev/shm
            try:
                shm_stat = os.statvfs('/dev/shm')
                shm_size = shm_stat.f_bavail * shm_stat.f_frsize / 1024 / 1024
                logger.info(f"/dev/shm 可用空间: {shm_size:.0f} MB")
                
                if shm_size < 64:
                    self.add_issue(f"/dev/shm空间不足: {shm_size:.0f} MB", "ERROR")
                    self.add_recommendation("增加/dev/shm大小或使用--disable-dev-shm-usage参数")
            except Exception as e:
                self.add_issue(f"无法检查/dev/shm: {e}", "WARNING")
            
            # 检查磁盘空间
            disk_stat = os.statvfs('.')
            disk_free = disk_stat.f_bavail * disk_stat.f_frsize / 1024 / 1024
            logger.info(f"当前目录可用磁盘空间: {disk_free:.0f} MB")
            
            if disk_free < 100:
                self.add_issue(f"磁盘空间不足: {disk_free:.0f} MB", "ERROR")
                self.add_recommendation("清理磁盘空间")
                
        except Exception as e:
            self.add_issue(f"检查内存和存储失败: {e}", "ERROR")
    
    async def check_playwright_installation(self):
        """检查Playwright安装"""
        logger.info("检查Playwright安装...")
        
        try:
            # 检查playwright命令
            result = subprocess.run(
                ['playwright', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"Playwright版本: {version}")
            else:
                self.add_issue("playwright命令不可用", "ERROR")
                self.add_recommendation("重新安装Playwright: pip install playwright")
                return
            
            # 检查浏览器安装
            result = subprocess.run(
                ['playwright', 'install', '--dry-run'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if "chromium" in result.stdout.lower() and "missing" in result.stdout.lower():
                self.add_issue("Chromium浏览器未安装", "ERROR")
                self.add_recommendation("安装浏览器: playwright install chromium")
            else:
                logger.info("Playwright浏览器检查通过")
                
        except subprocess.TimeoutExpired:
            self.add_issue("Playwright命令执行超时", "ERROR")
        except FileNotFoundError:
            self.add_issue("playwright命令未找到", "ERROR")
            self.add_recommendation("安装Playwright: pip install playwright")
        except Exception as e:
            self.add_issue(f"检查Playwright安装失败: {e}", "ERROR")
    
    async def check_browser_availability(self):
        """检查浏览器可用性"""
        logger.info("检查浏览器可用性...")
        
        try:
            # 查找Chromium可执行文件
            home_dir = Path.home()
            possible_paths = [
                home_dir / '.cache/ms-playwright/chromium-*/chrome-linux/chrome',
                Path('/usr/bin/chromium'),
                Path('/usr/bin/chromium-browser'),
                Path('/usr/bin/google-chrome'),
                Path('/snap/bin/chromium')
            ]
            
            found_browser = False
            for path_pattern in possible_paths:
                if '*' in str(path_pattern):
                    # 处理通配符路径
                    import glob
                    matches = glob.glob(str(path_pattern))
                    if matches:
                        logger.info(f"找到Playwright Chromium: {matches[0]}")
                        found_browser = True
                        break
                elif path_pattern.exists():
                    logger.info(f"找到系统浏览器: {path_pattern}")
                    found_browser = True
                    break
            
            if not found_browser:
                self.add_issue("未找到可用的浏览器", "ERROR")
                self.add_recommendation("安装浏览器: playwright install chromium")
            
        except Exception as e:
            self.add_issue(f"检查浏览器可用性失败: {e}", "WARNING")
    
    async def check_network_connectivity(self):
        """检查网络连接"""
        logger.info("检查网络连接...")
        
        try:
            # 测试DNS解析
            result = subprocess.run(
                ['nslookup', 'google.com'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("DNS解析正常")
            else:
                self.add_issue("DNS解析失败", "WARNING")
                self.add_recommendation("检查网络连接和DNS设置")
            
            # 测试HTTP连接
            result = subprocess.run(
                ['curl', '-I', '--connect-timeout', '10', 'https://www.google.com'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                logger.info("HTTP连接正常")
            else:
                self.add_issue("HTTP连接失败", "WARNING")
                self.add_recommendation("检查防火墙和代理设置")
                
        except subprocess.TimeoutExpired:
            self.add_issue("网络连接测试超时", "WARNING")
        except FileNotFoundError:
            logger.info("网络工具不可用，跳过网络测试")
        except Exception as e:
            self.add_issue(f"网络连接检查失败: {e}", "WARNING")
    
    async def check_permissions(self):
        """检查权限"""
        logger.info("检查权限...")
        
        try:
            # 检查当前目录写权限
            test_file = Path('./test_write_permission')
            try:
                test_file.write_text('test')
                test_file.unlink()
                logger.info("当前目录写权限正常")
            except Exception:
                self.add_issue("当前目录无写权限", "ERROR")
                self.add_recommendation("检查目录权限")
            
            # 检查是否以root用户运行
            if os.getuid() == 0:
                self.add_issue("以root用户运行", "WARNING")
                self.add_recommendation("建议使用非root用户运行，或添加--no-sandbox参数")
            
        except Exception as e:
            self.add_issue(f"权限检查失败: {e}", "WARNING")
    
    async def test_browser_launch(self):
        """测试浏览器启动"""
        logger.info("测试浏览器启动...")
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                # 测试最小配置启动
                try:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu'
                        ],
                        timeout=30000
                    )
                    
                    # 测试创建页面
                    page = await browser.new_page()
                    await page.goto('data:text/html,<h1>Test</h1>', timeout=10000)
                    content = await page.content()
                    
                    if 'Test' in content:
                        logger.info("浏览器启动测试成功")
                    else:
                        self.add_issue("浏览器页面加载异常", "WARNING")
                    
                    await page.close()
                    await browser.close()
                    
                except Exception as e:
                    self.add_issue(f"浏览器启动失败: {e}", "ERROR")
                    self.add_recommendation("检查系统依赖和Playwright安装")
                    
        except ImportError:
            self.add_issue("无法导入Playwright", "ERROR")
            self.add_recommendation("安装Playwright: pip install playwright")
        except Exception as e:
            self.add_issue(f"浏览器启动测试失败: {e}", "ERROR")
    
    def generate_report(self):
        """生成诊断报告"""
        logger.info("\n" + "="*50)
        logger.info("诊断报告")
        logger.info("="*50)
        
        if not self.issues:
            logger.info("✅ 未发现问题，环境配置正常")
        else:
            logger.info(f"发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                severity_icon = "🔴" if issue['severity'] == 'ERROR' else "🟡"
                logger.info(f"{i}. {severity_icon} [{issue['severity']}] {issue['issue']}")
        
        if self.recommendations:
            logger.info("\n建议解决方案:")
            for i, rec in enumerate(self.recommendations, 1):
                logger.info(f"{i}. {rec}")
        
        logger.info("\n快速修复命令:")
        logger.info("# 安装系统依赖")
        logger.info("sudo apt-get update && sudo apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2")
        logger.info("\n# 安装Playwright依赖")
        logger.info("playwright install-deps")
        logger.info("playwright install chromium")
        logger.info("\n# 使用Linux优化版爬虫")
        logger.info("python linux_crawler_fix.py")
        
        logger.info("\n" + "="*50)


async def main():
    """主函数"""
    diagnostic = LinuxDiagnostic()
    await diagnostic.run_full_diagnosis()


if __name__ == "__main__":
    asyncio.run(main())