#!/usr/bin/env python3
"""
无头模式启动脚本

此脚本强制使用无头模式启动Google商家Schema生成器，
并提供更详细的错误信息和解决方案。

使用方法:
    python run_headless.py [--port PORT] [--host HOST]
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path

# 添加app目录到Python路径
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def setup_environment():
    """设置环境变量"""
    # 强制无头模式
    os.environ["PLAYWRIGHT_HEADLESS"] = "true"
    os.environ["DISPLAY"] = ":99"  # 虚拟显示器
    
    # 禁用GPU相关功能
    os.environ["PLAYWRIGHT_CHROMIUM_USE_HEADLESS_NEW"] = "true"
    
    print("🔧 环境配置:")
    print(f"- 无头模式: 已启用")
    print(f"- 虚拟显示器: {os.environ.get('DISPLAY', '未设置')}")

def check_dependencies():
    """检查依赖"""
    print("\n📋 依赖检查:")
    
    missing_deps = []
    
    # 检查基础依赖
    try:
        import fastapi
        print(f"✅ FastAPI: {fastapi.__version__}")
    except ImportError:
        missing_deps.append("fastapi")
        print("❌ FastAPI: 未安装")
    
    try:
        import playwright
        print(f"✅ Playwright: {playwright.__version__}")
    except ImportError:
        missing_deps.append("playwright")
        print("❌ Playwright: 未安装")
    
    try:
        import uvicorn
        print(f"✅ Uvicorn: {uvicorn.__version__}")
    except ImportError:
        missing_deps.append("uvicorn")
        print("❌ Uvicorn: 未安装")
    
    if missing_deps:
        print(f"\n❌ 缺少依赖: {', '.join(missing_deps)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

async def test_crawler():
    """测试爬虫功能"""
    print("\n🧪 测试爬虫启动...")
    
    try:
        from crawler import GoogleBusinessCrawler
        
        crawler = GoogleBusinessCrawler()
        await crawler.start()
        print("✅ 爬虫启动成功")
        await crawler.stop()
        print("✅ 爬虫停止成功")
        return True
        
    except Exception as e:
        print(f"❌ 爬虫测试失败: {e}")
        
        # 提供详细的错误分析
        error_str = str(e)
        if "Host system is missing dependencies" in error_str:
            print("\n🔧 解决方案:")
            print("1. 运行依赖修复脚本: python fix_playwright_deps.py")
            print("2. 手动安装依赖:")
            print("   playwright install-deps")
            print("   playwright install chromium")
            print("3. 使用Docker部署（推荐）:")
            print("   docker-compose up -d")
        elif "executable_path" in error_str or "browser" in error_str.lower():
            print("\n🔧 浏览器问题解决方案:")
            print("1. 重新安装Playwright浏览器: playwright install chromium")
            print("2. 检查系统架构兼容性")
            print("3. 使用Docker部署")
        else:
            print("\n🔧 通用解决方案:")
            print("1. 检查Python版本兼容性")
            print("2. 重新安装依赖: pip install -r requirements.txt")
            print("3. 使用Docker部署")
        
        return False

def start_server(host="0.0.0.0", port=8000):
    """启动服务器"""
    print(f"\n🚀 启动服务器 {host}:{port}...")
    
    try:
        import uvicorn
        from main import app
        
        # 配置uvicorn
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        server.run()
        
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        
        # 提供启动失败的解决方案
        print("\n🔧 服务器启动失败解决方案:")
        print("1. 检查端口是否被占用: lsof -i :8000")
        print("2. 尝试其他端口: python run_headless.py --port 8001")
        print("3. 检查防火墙设置")
        print("4. 查看详细错误日志")
        
        return False
    
    return True

def show_usage_info(host, port):
    """显示使用信息"""
    print("\n" + "=" * 60)
    print("🎉 Google商家Schema生成器启动成功！")
    print("=" * 60)
    print(f"📍 服务地址: http://{host}:{port}")
    if host == "0.0.0.0":
        print(f"📍 本地访问: http://localhost:{port}")
        print(f"📍 局域网访问: http://[您的IP地址]:{port}")
    print("\n📖 使用说明:")
    print("1. 在浏览器中打开上述地址")
    print("2. 输入Google商家URL")
    print("3. 点击生成Schema")
    print("4. 复制生成的JSON-LD代码")
    print("\n⏹️  停止服务: Ctrl+C")
    print("=" * 60)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Google商家Schema生成器 - 无头模式启动")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口 (默认: 8000)")
    parser.add_argument("--test-only", action="store_true", help="仅测试不启动服务器")
    
    args = parser.parse_args()
    
    print("🔧 Google商家Schema生成器 - 无头模式启动")
    print("=" * 60)
    
    # 设置环境
    setup_environment()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装依赖")
        print("运行: pip install -r requirements.txt")
        sys.exit(1)
    
    # 测试爬虫
    if not await test_crawler():
        print("\n❌ 爬虫测试失败")
        if not args.test_only:
            print("\n⚠️  尽管爬虫测试失败，仍可尝试启动服务器")
            print("某些功能可能不可用，建议先解决依赖问题")
            
            response = input("\n是否继续启动服务器？(y/N): ")
            if response.lower() != 'y':
                print("启动已取消")
                sys.exit(1)
        else:
            sys.exit(1)
    
    if args.test_only:
        print("\n✅ 测试完成")
        return
    
    # 显示使用信息
    show_usage_info(args.host, args.port)
    
    # 启动服务器
    start_server(args.host, args.port)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n🔧 建议解决方案:")
        print("1. 运行依赖修复脚本: python fix_playwright_deps.py")
        print("2. 使用Docker部署: docker-compose up -d")
        print("3. 检查系统兼容性")
        sys.exit(1)