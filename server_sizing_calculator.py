#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器规格计算器

根据并发需求计算合适的服务器配置
"""

import math
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class ServerSpec:
    """服务器规格"""
    cpu_cores: int
    memory_gb: int
    storage_gb: int
    bandwidth_mbps: int
    estimated_cost_usd: float
    provider: str
    instance_type: str

@dataclass
class WorkloadRequirement:
    """工作负载需求"""
    concurrent_requests: int
    scenario: str  # 'cache' or 'browser'
    avg_response_time_ms: int
    memory_per_request_mb: float
    cpu_per_request: float

class ServerSizingCalculator:
    """服务器规格计算器"""
    
    def __init__(self):
        # 基础性能参数
        self.base_memory_mb = 512  # 系统基础内存
        self.base_cpu_usage = 0.1  # 系统基础CPU使用率
        
        # 缓存查询场景参数
        self.cache_memory_per_request = 2.0  # MB
        self.cache_cpu_per_request = 0.01  # CPU核心占用
        self.cache_response_time = 50  # ms
        
        # 浏览器爬取场景参数
        self.browser_memory_per_instance = 20.0  # MB (基于之前的测试)
        self.browser_cpu_per_instance = 0.15  # CPU核心占用
        self.browser_response_time = 3000  # ms
        
    def calculate_cache_requirements(self, concurrent_requests: int) -> Dict[str, float]:
        """计算缓存查询场景的资源需求"""
        # 内存需求
        memory_for_requests = concurrent_requests * self.cache_memory_per_request
        total_memory_mb = self.base_memory_mb + memory_for_requests
        
        # CPU需求 (考虑突发流量，预留50%余量)
        cpu_for_requests = concurrent_requests * self.cache_cpu_per_request
        total_cpu_cores = (self.base_cpu_usage + cpu_for_requests) * 1.5
        
        # 网络带宽需求 (假设每个请求平均10KB响应)
        avg_response_size_kb = 10
        requests_per_second = concurrent_requests / (self.cache_response_time / 1000)
        bandwidth_mbps = (requests_per_second * avg_response_size_kb * 8) / 1024  # Mbps
        
        return {
            'memory_mb': total_memory_mb,
            'cpu_cores': total_cpu_cores,
            'bandwidth_mbps': bandwidth_mbps * 2,  # 上下行带宽
            'requests_per_second': requests_per_second
        }
    
    def calculate_browser_requirements(self, concurrent_requests: int) -> Dict[str, float]:
        """计算浏览器爬取场景的资源需求"""
        # 内存需求 (每个浏览器实例)
        memory_for_browsers = concurrent_requests * self.browser_memory_per_instance
        total_memory_mb = self.base_memory_mb + memory_for_browsers
        
        # CPU需求 (浏览器渲染需要更多CPU)
        cpu_for_browsers = concurrent_requests * self.browser_cpu_per_instance
        total_cpu_cores = (self.base_cpu_usage + cpu_for_browsers) * 1.3
        
        # 网络带宽需求 (浏览器需要下载更多资源)
        avg_response_size_kb = 100  # 包含图片、CSS、JS等
        requests_per_second = concurrent_requests / (self.browser_response_time / 1000)
        bandwidth_mbps = (requests_per_second * avg_response_size_kb * 8) / 1024
        
        return {
            'memory_mb': total_memory_mb,
            'cpu_cores': total_cpu_cores,
            'bandwidth_mbps': bandwidth_mbps * 2,
            'requests_per_second': requests_per_second
        }
    
    def get_server_recommendations(self, cache_concurrent: int, browser_concurrent: int) -> List[ServerSpec]:
        """获取服务器推荐配置"""
        # 计算两种场景的需求
        cache_req = self.calculate_cache_requirements(cache_concurrent)
        browser_req = self.calculate_browser_requirements(browser_concurrent)
        
        # 取最大值作为服务器规格
        max_memory_gb = math.ceil(max(cache_req['memory_mb'], browser_req['memory_mb']) / 1024)
        max_cpu_cores = math.ceil(max(cache_req['cpu_cores'], browser_req['cpu_cores']))
        max_bandwidth = math.ceil(max(cache_req['bandwidth_mbps'], browser_req['bandwidth_mbps']))
        
        # 存储需求 (日志、缓存、临时文件)
        storage_gb = max(50, max_memory_gb * 2)  # 至少50GB，或内存的2倍
        
        recommendations = []
        
        # 云服务器推荐配置
        cloud_configs = [
            {
                'provider': '阿里云',
                'specs': [
                    {'type': 'ecs.c6.2xlarge', 'cpu': 8, 'memory': 16, 'cost': 180},
                    {'type': 'ecs.c6.4xlarge', 'cpu': 16, 'memory': 32, 'cost': 360},
                    {'type': 'ecs.c6.8xlarge', 'cpu': 32, 'memory': 64, 'cost': 720},
                ]
            },
            {
                'provider': '腾讯云',
                'specs': [
                    {'type': 'S5.2XLARGE16', 'cpu': 8, 'memory': 16, 'cost': 170},
                    {'type': 'S5.4XLARGE32', 'cpu': 16, 'memory': 32, 'cost': 340},
                    {'type': 'S5.8XLARGE64', 'cpu': 32, 'memory': 64, 'cost': 680},
                ]
            },
            {
                'provider': 'AWS',
                'specs': [
                    {'type': 'c5.2xlarge', 'cpu': 8, 'memory': 16, 'cost': 200},
                    {'type': 'c5.4xlarge', 'cpu': 16, 'memory': 32, 'cost': 400},
                    {'type': 'c5.9xlarge', 'cpu': 36, 'memory': 72, 'cost': 900},
                ]
            }
        ]
        
        for provider_config in cloud_configs:
            provider = provider_config['provider']
            for spec in provider_config['specs']:
                if spec['cpu'] >= max_cpu_cores and spec['memory'] >= max_memory_gb:
                    recommendations.append(ServerSpec(
                        cpu_cores=spec['cpu'],
                        memory_gb=spec['memory'],
                        storage_gb=storage_gb,
                        bandwidth_mbps=max_bandwidth,
                        estimated_cost_usd=spec['cost'],
                        provider=provider,
                        instance_type=spec['type']
                    ))
        
        # 按性价比排序
        recommendations.sort(key=lambda x: x.estimated_cost_usd / (x.cpu_cores * x.memory_gb))
        
        return recommendations[:6]  # 返回前6个推荐
    
    def print_detailed_analysis(self, cache_concurrent: int, browser_concurrent: int):
        """打印详细分析报告"""
        print("=" * 80)
        print("服务器规格需求分析报告")
        print("=" * 80)
        
        # 场景需求分析
        cache_req = self.calculate_cache_requirements(cache_concurrent)
        browser_req = self.calculate_browser_requirements(browser_concurrent)
        
        print(f"\n📊 场景1: 缓存查询 ({cache_concurrent}并发)")
        print(f"  内存需求: {cache_req['memory_mb']:.1f}MB ({cache_req['memory_mb']/1024:.1f}GB)")
        print(f"  CPU需求: {cache_req['cpu_cores']:.1f}核心")
        print(f"  带宽需求: {cache_req['bandwidth_mbps']:.1f}Mbps")
        print(f"  处理能力: {cache_req['requests_per_second']:.1f}请求/秒")
        
        print(f"\n📊 场景2: 浏览器爬取 ({browser_concurrent}并发)")
        print(f"  内存需求: {browser_req['memory_mb']:.1f}MB ({browser_req['memory_mb']/1024:.1f}GB)")
        print(f"  CPU需求: {browser_req['cpu_cores']:.1f}核心")
        print(f"  带宽需求: {browser_req['bandwidth_mbps']:.1f}Mbps")
        print(f"  处理能力: {browser_req['requests_per_second']:.1f}请求/秒")
        
        # 推荐配置
        recommendations = self.get_server_recommendations(cache_concurrent, browser_concurrent)
        
        print("\n🏆 推荐服务器配置")
        print("-" * 80)
        print(f"{'供应商':<8} {'实例类型':<16} {'CPU':<4} {'内存':<6} {'月费用':<8} {'性价比':<8}")
        print("-" * 80)
        
        for i, spec in enumerate(recommendations):
            performance_score = spec.cpu_cores * spec.memory_gb
            cost_efficiency = performance_score / spec.estimated_cost_usd
            
            print(f"{spec.provider:<8} {spec.instance_type:<16} {spec.cpu_cores:<4} {spec.memory_gb:<6}GB ${spec.estimated_cost_usd:<7.0f} {cost_efficiency:<8.2f}")
            
            if i == 0:
                print("         ⭐ 最佳性价比推荐")
        
        # 部署建议
        print("\n💡 部署建议")
        print("-" * 40)
        
        best_spec = recommendations[0] if recommendations else None
        if best_spec:
            print(f"✅ 推荐配置: {best_spec.provider} {best_spec.instance_type}")
            print(f"   - CPU: {best_spec.cpu_cores}核心")
            print(f"   - 内存: {best_spec.memory_gb}GB")
            print(f"   - 存储: {best_spec.storage_gb}GB SSD")
            print(f"   - 带宽: {best_spec.bandwidth_mbps}Mbps")
            print(f"   - 预估月费用: ${best_spec.estimated_cost_usd}")
        
        print("\n🔧 优化建议")
        print("1. 使用Redis缓存减少数据库查询")
        print("2. 实现浏览器实例池，复用浏览器连接")
        print("3. 配置负载均衡，支持水平扩展")
        print("4. 监控CPU和内存使用率，及时调整")
        print("5. 使用CDN加速静态资源访问")
        
        print("\n⚠️  注意事项")
        print("1. 浏览器爬取场景建议预留30%资源余量")
        print("2. 高并发时考虑使用容器化部署")
        print("3. 定期清理浏览器缓存和临时文件")
        print("4. 配置自动重启机制，防止内存泄漏")

def main():
    """主函数"""
    calculator = ServerSizingCalculator()
    
    # 用户需求
    cache_concurrent = 1000  # 缓存查询并发
    browser_concurrent = 50  # 浏览器爬取并发
    
    calculator.print_detailed_analysis(cache_concurrent, browser_concurrent)

if __name__ == "__main__":
    main()