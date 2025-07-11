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
        self.monitor_config = None  # 保存监控服务器配置以便重启
        
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
    
    def restart_monitor_server(self):
        """重启监控服务器"""
        if not self.monitor_config:
            print("❌ 没有监控服务器配置信息")
            return False
            
        print("🔄 尝试重启监控服务器...")
        
        # 停止现有的监控服务器进程
        for i, (service_name, process) in enumerate(self.processes):
            if service_name == "监控服务器":
                try:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=3)
                except:
                    pass
                # 从进程列表中移除
                self.processes.pop(i)
                break
        
        # 启动新的监控服务器进程
        try:
            monitor_process = self.start_monitor_server(
                self.monitor_config['host'],
                self.monitor_config['port'],
                self.monitor_config['api_host'],
                self.monitor_config['api_port']
            )
            time.sleep(2)
            
            if self.wait_for_startup(monitor_process, "监控服务器"):
                print("✅ 监控服务器重启成功")
                return True
            else:
                print("❌ 监控服务器重启失败")
                # 从进程列表中移除失败的进程
                self.processes = [(name, proc) for name, proc in self.processes if name != "监控服务器"]
                return False
        except Exception as e:
            print(f"❌ 重启监控服务器时出错: {e}")
            return False
    
    def wait_for_startup(self, process, service_name, timeout=30):
        """等待服务启动"""
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                print(f"❌ {service_name}启动失败")
                # 输出所有收集到的错误信息
                if output_lines:
                    print(f"[{service_name}] 错误详情:")
                    for line in output_lines[-10:]:  # 显示最后10行
                        print(f"[{service_name}] {line}")
                return False
            
            # 检查是否有输出表明服务已启动
            try:
                line = process.stdout.readline()
                if line:
                    line_stripped = line.strip()
                    output_lines.append(line_stripped)
                    print(f"[{service_name}] {line_stripped}")
                    if ("Uvicorn running on" in line or 
                        "Application startup complete" in line or
                        "监控服务器启动完成" in line or
                        "INFO:     Started server process" in line):
                        print(f"✅ {service_name}启动成功")
                        return True
            except:
                pass
            
            time.sleep(0.1)
        
        print(f"⏰ {service_name}启动超时")
        # 输出超时时的错误信息
        if output_lines:
            print(f"[{service_name}] 超时前的输出:")
            for line in output_lines[-10:]:  # 显示最后10行
                print(f"[{service_name}] {line}")
        return False
    
    def monitor_processes(self):
        """监控进程状态"""
        print("\n🔍 监控服务状态...")
        print("按 Ctrl+C 停止所有服务")
        if self.monitor_config:
            print("💡 提示: 如果监控服务器失败，您可以在另一个终端运行以下命令重启:")
            print(f"   python start_with_monitor.py --monitor-only --monitor-port {self.monitor_config['port']} --api-port {self.monitor_config['api_port']}")
        
        try:
            while True:
                api_running = True
                stopped_services = []
                
                for service_name, process in self.processes:
                    if process.poll() is not None:
                        print(f"❌ {service_name}已停止")
                        stopped_services.append(service_name)
                        if service_name == "API服务器":
                            api_running = False
                
                # 只有当API服务器停止时才关闭所有服务
                if not api_running:
                    print("API服务器已停止，正在关闭所有服务...")
                    break
                elif stopped_services:
                    # 从进程列表中移除已停止的服务
                    self.processes = [(name, proc) for name, proc in self.processes if name not in stopped_services]
                
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
            # 保存监控服务器配置
            manager.monitor_config = {
                'host': args.monitor_host,
                'port': args.monitor_port,
                'api_host': "127.0.0.1",
                'api_port': args.api_port
            }
            
            monitor_process = manager.start_monitor_server(
                args.monitor_host, 
                args.monitor_port,
                "127.0.0.1",  # 监控本地API服务器
                args.api_port
            )
            time.sleep(2)  # 等待监控服务器启动
            
            if not manager.wait_for_startup(monitor_process, "监控服务器"):
                print("⚠️  监控服务器启动失败，但API服务器继续运行")
                print("💡 您仍然可以使用API服务器的所有功能")
                print("🔧 监控服务器问题可能的原因:")
                print("   - 端口8001被占用 (尝试: lsof -i :8001)")
                print("   - 静态文件缺失 (检查: static/monitor.html)")
                print("   - 依赖包问题 (尝试: pip install -r requirements.txt)")
                print("   - API服务器未完全启动 (等待几秒后重试)")
                print("\n🔄 重启监控服务器的方法:")
                print(f"   python start_with_monitor.py --monitor-only --monitor-port {args.monitor_port} --api-port {args.api_port}")
                # 从进程列表中移除失败的监控服务器进程
                manager.processes = [(name, proc) for name, proc in manager.processes if name != "监控服务器"]
                # 终止失败的监控服务器进程
                try:
                    if monitor_process.poll() is None:
                        monitor_process.terminate()
                        monitor_process.wait(timeout=3)
                except:
                    pass
        
        print("\n" + "=" * 50)
        print("🎉 服务启动完成!")
        
        # 检查哪些服务实际在运行
        running_services = [name for name, proc in manager.processes if proc.poll() is None]
        
        if not args.monitor_only and "API服务器" in running_services:
            print(f"📡 API服务器: http://0.0.0.0:{args.api_port}")
            print(f"📚 API文档: http://0.0.0.0:{args.api_port}/docs")

        if not args.no_monitor and "监控服务器" in running_services:
            print(f"🔍 监控中心: http://0.0.0.0:{args.monitor_port}")
        elif not args.no_monitor:
            print("⚠️  监控中心不可用 (启动失败)")
        
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