#!/usr/bin/env python3
"""开发服务器运行器"""

import os
import sys
from pathlib import Path

# 将app目录添加到Python路径
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # 为开发设置环境变量
    os.environ.setdefault("PYTHONPATH", str(app_dir))
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='启动Google商家Schema生成器')
    parser.add_argument('--port', type=int, default=8000, help='服务器端口 (默认: 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器主机 (默认: 0.0.0.0)')
    args = parser.parse_args()
    
    print("启动Google商家Schema生成器...")
    print(f"服务器将在以下地址可用: http://localhost:{args.port}")
    print(f"API文档: http://localhost:{args.port}/docs")
    print("按Ctrl+C停止服务器")
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=True,
        log_level="info",
        access_log=True


    )