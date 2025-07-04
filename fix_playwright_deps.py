#!/usr/bin/env python3
"""
Playwright依赖修复脚本

此脚本帮助解决Playwright浏览器依赖缺失的问题。
适用于在服务器环境中部署Google商家Schema生成器时遇到的依赖问题。

使用方法:
    python fix_playwright_deps.py
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(command, description):
    """运行命令并处理错误"""
    print(f"\n🔧 {description}...")
    print(f"执行命令: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} 成功")
            if result.stdout:
                print(f"输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} 失败")
            if result.stderr:
                print(f"错误: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} 执行异常: {e}")
        return False

def check_system_info():
    """检查系统信息"""
    print("📋 系统信息检查:")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"Python版本: {sys.version}")
    
    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"虚拟环境: {sys.prefix}")
    else:
        print("虚拟环境: 未使用")

def check_playwright_installation():
    """检查Playwright安装状态"""
    print("\n🔍 检查Playwright安装状态...")
    
    try:
        import playwright
        print(f"✅ Playwright已安装，版本: {playwright.__version__}")
        return True
    except ImportError:
        print("❌ Playwright未安装")
        return False

def install_playwright_deps():
    """安装Playwright依赖"""
    print("\n🚀 开始修复Playwright依赖...")
    
    # 1. 安装/升级Playwright
    if not run_command("pip install --upgrade playwright", "安装/升级Playwright"):
        print("❌ Playwright安装失败，请检查网络连接")
        return False
    
    # 2. 安装系统依赖
    system = platform.system().lower()
    if system == "linux":
        print("\n🐧 检测到Linux系统，安装系统依赖...")
        
        # 尝试安装系统依赖
        success = run_command("playwright install-deps", "安装系统依赖")
        if not success:
            print("⚠️  自动安装系统依赖失败，请手动安装")
            print("对于Ubuntu/Debian系统，请运行:")
            print("sudo apt-get update")
            print("sudo apt-get install -y libatk-bridge2.0-0 libatspi2.0-0 libgbm1")
            print("\n对于CentOS/RHEL系统，请运行:")
            print("sudo yum install -y atk at-spi2-atk mesa-libgbm")
    
    # 3. 安装浏览器
    if not run_command("playwright install chromium", "安装Chromium浏览器"):
        print("❌ Chromium安装失败")
        return False
    
    return True

def test_playwright():
    """测试Playwright是否正常工作"""
    print("\n🧪 测试Playwright功能...")
    
    test_script = '''
import asyncio
from playwright.async_api import async_playwright

async def test():
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process'
            ]
        )
        page = await browser.new_page()
        await page.goto('https://www.google.com')
        title = await page.title()
        await browser.close()
        await playwright.stop()
        print(f"✅ 测试成功，页面标题: {title}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test())
'''
    
    # 写入临时测试文件
    test_file = Path("playwright_test.py")
    try:
        test_file.write_text(test_script)
        result = subprocess.run([sys.executable, str(test_file)], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Playwright功能测试通过")
            return True
        else:
            print("❌ Playwright功能测试失败")
            if result.stderr:
                print(f"错误信息: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()

def show_docker_alternative():
    """显示Docker替代方案"""
    print("\n🐳 Docker部署方案（推荐）:")
    print("如果依赖安装仍有问题，强烈建议使用Docker部署:")
    print("")
    print("1. 构建Docker镜像:")
    print("   docker-compose build")
    print("")
    print("2. 启动服务:")
    print("   docker-compose up -d")
    print("")
    print("3. 查看日志:")
    print("   docker-compose logs -f")
    print("")
    print("Docker方案的优势:")
    print("- 无需手动安装系统依赖")
    print("- 环境一致性保证")
    print("- 部署简单可靠")

def main():
    """主函数"""
    print("🔧 Google商家Schema生成器 - Playwright依赖修复工具")
    print("=" * 60)
    
    # 检查系统信息
    check_system_info()
    
    # 检查Playwright安装状态
    playwright_installed = check_playwright_installation()
    
    # 安装依赖
    if install_playwright_deps():
        print("\n✅ 依赖安装完成")
        
        # 测试功能
        if test_playwright():
            print("\n🎉 Playwright修复成功！")
            print("现在可以正常启动Google商家Schema生成器了:")
            print("python run.py")
        else:
            print("\n⚠️  Playwright安装完成但测试失败")
            show_docker_alternative()
    else:
        print("\n❌ 依赖安装失败")
        show_docker_alternative()
    
    print("\n" + "=" * 60)
    print("修复完成！")

if __name__ == "__main__":
    main()