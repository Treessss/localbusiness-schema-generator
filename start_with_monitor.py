#!/usr/bin/env python3
"""
同时启动主API服务器和监控服务器的便捷脚本
"""

import os
import sys
import time
import signal
import argparse
import subprocess
from pathlib import Path


class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.processes = []
        self.project_root = Path(__file__).parent
        
    def start_api_server(self, host="0.0.0.0", port=8000):
        """启动主API服务器"""
        print(f"启动主API服务器 (端口: {port})...")
        
        cmd = [
            sys.executable, "run.py",
            "--host", host,
            "--port", str(port)
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.processes.append(("API服务器", process))
        return process
    
    def start_monitor_server(self, host="0.0.0.0", port=8001, api_host="localhost", api_port=8000):
        """启动监控服务器"""
        print(f"启动监控服务器 (端口: {port})...")
        
        cmd = [
            sys.executable, "monitor.py",
            "--host", host,
            "--port", str(port),
            "--api-host", api_host,
            "--api-port", str(api_port)
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.processes.append(("监控服务器", process))
        return process
    
    def wait_for_startup(self, process, service_name, timeout=30):
        """等待服务启动"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                print(f"❌ {service_name}启动失败")
                return False
            
            # 检查是否有输出表明服务已启动
            try:
                line = process.stdout.readline()
                if line:
                    print(f"[{service_name}] {line.strip()}")
                    if "Uvicorn running on" in line or "Application startup complete" in line:
                        print(f"✅ {service_name}启动成功")
                        return True
            except:
                pass
            
            time.sleep(0.1)
        
        print(f"⏰ {service_name}启动超时")
        return False
    
    def monitor_processes(self):
        """监控进程状态"""
        print("\n🔍 监控服务状态...")
        print("按 Ctrl+C 停止所有服务")
        
        try:
            while True:
                all_running = True
                
                for service_name, process in self.processes:
                    if process.poll() is not None:
                        print(f"❌ {service_name}已停止")
                        all_running = False
                
                if not all_running:
                    print("检测到服务停止，正在关闭所有服务...")
                    break
                
                # 输出进程日志
                for service_name, process in self.processes:
                    try:
                        while True:
                            line = process.stdout.readline()
                            if not line:
                                break
                            print(f"[{service_name}] {line.strip()}")
                    except:
                        pass
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n收到停止信号，正在关闭所有服务...")
        
        self.stop_all_services()
    
    def stop_all_services(self):
        """停止所有服务"""
        for service_name, process in self.processes:
            if process.poll() is None:
                print(f"停止 {service_name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"强制停止 {service_name}...")
                    process.kill()
                    process.wait()
                except Exception as e:
                    print(f"停止 {service_name} 时出错: {e}")
        
        print("所有服务已停止")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n收到信号 {signum}，正在停止服务...")
        self.stop_all_services()
        sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='同时启动API服务器和监控服务器')
    
    # API服务器参数
    parser.add_argument('--api-port', type=int, default=8000, help='API服务器端口 (默认: 8000)')
    parser.add_argument('--api-host', type=str, default='0.0.0.0', help='API服务器主机 (默认: 0.0.0.0)')
    
    # 监控服务器参数
    parser.add_argument('--monitor-port', type=int, default=8001, help='监控服务器端口 (默认: 8001)')
    parser.add_argument('--monitor-host', type=str, default='0.0.0.0', help='监控服务器主机 (默认: 0.0.0.0)')
    
    # 其他选项
    parser.add_argument('--no-monitor', action='store_true', help='只启动API服务器，不启动监控服务器')
    parser.add_argument('--monitor-only', action='store_true', help='只启动监控服务器，不启动API服务器')
    
    args = parser.parse_args()
    
    # 创建服务管理器
    manager = ServiceManager()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    print("🚀 启动服务...")
    print("=" * 50)
    
    try:
        # 启动API服务器
        if not args.monitor_only:
            api_process = manager.start_api_server(args.api_host, args.api_port)
            time.sleep(2)  # 等待API服务器启动
            
            if not manager.wait_for_startup(api_process, "API服务器"):
                print("API服务器启动失败，退出")
                return
        
        # 启动监控服务器
        if not args.no_monitor:
            monitor_process = manager.start_monitor_server(
                args.monitor_host, 
                args.monitor_port,
                "localhost",  # 监控本地API服务器
                args.api_port
            )
            time.sleep(2)  # 等待监控服务器启动
            
            if not manager.wait_for_startup(monitor_process, "监控服务器"):
                print("监控服务器启动失败，但API服务器继续运行")
        
        print("\n" + "=" * 50)
        print("🎉 服务启动完成!")
        
        if not args.monitor_only:
            print(f"📡 API服务器: http://localhost:{args.api_port}")
            print(f"📚 API文档: http://localhost:{args.api_port}/docs")
            print(f"📊 内置统计: http://localhost:{args.api_port}/stats")
        
        if not args.no_monitor:
            print(f"🔍 监控中心: http://localhost:{args.monitor_port}")
        
        print("=" * 50)
        
        # 监控进程
        manager.monitor_processes()
        
    except Exception as e:
        print(f"启动服务时出错: {e}")
        manager.stop_all_services()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())