#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速服务器配置对比工具
"""

from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ServerOption:
    """服务器选项"""
    name: str
    provider: str
    instance_type: str
    cpu_cores: int
    memory_gb: int
    monthly_cost_usd: int
    performance_score: float
    recommended_for: str
    pros: List[str]
    cons: List[str]

def get_server_options() -> List[ServerOption]:
    """获取服务器选项列表"""
    return [
        ServerOption(
            name="经济型方案",
            provider="腾讯云",
            instance_type="S5.4XLARGE32",
            cpu_cores=16,
            memory_gb=32,
            monthly_cost_usd=340,
            performance_score=7.5,
            recommended_for="中小型业务，预算有限",
            pros=["成本低", "满足基本需求", "易于管理"],
            cons=["扩展性有限", "高峰期可能性能不足"]
        ),
        ServerOption(
            name="推荐方案 ⭐",
            provider="腾讯云",
            instance_type="S5.8XLARGE64",
            cpu_cores=32,
            memory_gb=64,
            monthly_cost_usd=680,
            performance_score=9.2,
            recommended_for="生产环境，平衡性能与成本",
            pros=["性价比最高", "性能充足", "支持高并发", "扩展性好"],
            cons=["成本中等"]
        ),
        ServerOption(
            name="高性能方案",
            provider="腾讯云",
            instance_type="S5.12XLARGE96",
            cpu_cores=48,
            memory_gb=96,
            monthly_cost_usd=1020,
            performance_score=9.8,
            recommended_for="大型企业，超高并发需求",
            pros=["性能最强", "未来扩展空间大", "稳定性极高"],
            cons=["成本较高", "可能存在资源浪费"]
        ),
        ServerOption(
            name="阿里云方案",
            provider="阿里云",
            instance_type="ecs.c6.8xlarge",
            cpu_cores=32,
            memory_gb=64,
            monthly_cost_usd=720,
            performance_score=9.0,
            recommended_for="需要阿里云生态的业务",
            pros=["生态完善", "技术支持好", "国内访问快"],
            cons=["价格略高于腾讯云"]
        ),
        ServerOption(
            name="AWS方案",
            provider="AWS",
            instance_type="c5.9xlarge",
            cpu_cores=36,
            memory_gb=72,
            monthly_cost_usd=900,
            performance_score=9.5,
            recommended_for="国际业务，全球部署",
            pros=["全球覆盖", "服务最全", "技术领先"],
            cons=["价格最高", "国内访问可能较慢"]
        )
    ]

def print_comparison_table():
    """打印对比表格"""
    options = get_server_options()
    
    print("\n" + "=" * 100)
    print("🚀 服务器配置快速对比表")
    print("=" * 100)
    
    # 表头
    print(f"{'方案':<12} {'供应商':<8} {'实例类型':<16} {'CPU':<4} {'内存':<6} {'月费用':<8} {'性能':<6} {'推荐场景':<20}")
    print("-" * 100)
    
    # 数据行
    for option in options:
        print(f"{option.name:<12} {option.provider:<8} {option.instance_type:<16} {option.cpu_cores:<4} {option.memory_gb:<6}GB ${option.monthly_cost_usd:<7} {option.performance_score:<6} {option.recommended_for:<20}")
    
    print("\n💰 年费用对比 (含预留实例折扣)")
    print("-" * 60)
    print(f"{'方案':<12} {'标准年费用':<12} {'预留实例年费用':<16} {'节省金额':<10}")
    print("-" * 60)
    
    for option in options:
        standard_yearly = option.monthly_cost_usd * 12
        reserved_yearly = int(standard_yearly * 0.6)  # 40% 折扣
        savings = standard_yearly - reserved_yearly
        
        print(f"{option.name:<12} ${standard_yearly:<11} ${reserved_yearly:<15} ${savings:<9}")

def print_detailed_analysis():
    """打印详细分析"""
    options = get_server_options()
    
    print("\n" + "=" * 80)
    print("📊 详细方案分析")
    print("=" * 80)
    
    for i, option in enumerate(options, 1):
        print(f"\n{i}. {option.name} - {option.provider} {option.instance_type}")
        print(f"   配置: {option.cpu_cores}核/{option.memory_gb}GB")
        print(f"   费用: ${option.monthly_cost_usd}/月")
        print(f"   性能评分: {option.performance_score}/10")
        print(f"   适用场景: {option.recommended_for}")
        
        print("   ✅ 优势:")
        for pro in option.pros:
            print(f"      • {pro}")
        
        print("   ⚠️ 劣势:")
        for con in option.cons:
            print(f"      • {con}")
        
        if "⭐" in option.name:
            print("   🏆 最佳推荐方案")

def print_capacity_planning():
    """打印容量规划"""
    print("\n" + "=" * 80)
    print("📈 容量规划分析")
    print("=" * 80)
    
    print("\n🎯 并发处理能力对比")
    print("-" * 50)
    
    scenarios = [
        {"name": "缓存查询", "target": 1000, "cpu_per_req": 0.01, "mem_per_req": 2},
        {"name": "浏览器爬取", "target": 50, "cpu_per_req": 0.15, "mem_per_req": 20}
    ]
    
    options = get_server_options()
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['name']}场景 (目标: {scenario['target']}并发)")
        print(f"{'方案':<12} {'最大并发':<10} {'CPU余量':<10} {'内存余量':<10} {'状态':<8}")
        print("-" * 50)
        
        for option in options:
            max_cpu_concurrent = int((option.cpu_cores * 0.8) / scenario['cpu_per_req'])
            max_mem_concurrent = int((option.memory_gb * 1024 * 0.8) / scenario['mem_per_req'])
            max_concurrent = min(max_cpu_concurrent, max_mem_concurrent)
            
            cpu_usage = (scenario['target'] * scenario['cpu_per_req'] / option.cpu_cores) * 100
            mem_usage = (scenario['target'] * scenario['mem_per_req'] / (option.memory_gb * 1024)) * 100
            
            status = "✅充足" if max_concurrent >= scenario['target'] else "❌不足"
            
            print(f"{option.name:<12} {max_concurrent:<10} {100-cpu_usage:<9.1f}% {100-mem_usage:<9.1f}% {status:<8}")

def print_cost_optimization():
    """打印成本优化建议"""
    print("\n" + "=" * 80)
    print("💡 成本优化建议")
    print("=" * 80)
    
    print("\n🔧 优化策略:")
    strategies = [
        "使用预留实例: 可节省40%费用",
        "按量付费: 测试环境使用，避免资源浪费",
        "自动伸缩: 根据负载动态调整实例数量",
        "混合部署: 缓存查询用小实例，爬取用大实例",
        "定时任务: 非高峰期关闭部分实例",
        "监控优化: 实时监控资源使用，及时调整"
    ]
    
    for i, strategy in enumerate(strategies, 1):
        print(f"   {i}. {strategy}")
    
    print("\n💰 分阶段部署建议:")
    phases = [
        {"phase": "测试阶段", "config": "S5.4XLARGE32", "cost": "$340/月", "desc": "验证功能和性能"},
        {"phase": "小规模生产", "config": "S5.8XLARGE64", "cost": "$680/月", "desc": "支持中等并发"},
        {"phase": "大规模生产", "config": "多实例集群", "cost": "$1500+/月", "desc": "水平扩展架构"}
    ]
    
    for phase in phases:
        print(f"   📅 {phase['phase']}: {phase['config']} ({phase['cost']}) - {phase['desc']}")

def main():
    """主函数"""
    print("🎯 针对您的需求 (缓存查询1000并发 + 浏览器爬取50并发)")
    
    print_comparison_table()
    print_detailed_analysis()
    print_capacity_planning()
    print_cost_optimization()
    
    print("\n" + "=" * 80)
    print("🏆 最终建议")
    print("=" * 80)
    print("\n✅ 生产环境推荐: 腾讯云 S5.8XLARGE64")
    print("   • 32核/64GB配置完全满足需求")
    print("   • 性价比最高，月费用$680")
    print("   • 支持未来业务增长")
    print("   • 技术支持和稳定性良好")
    
    print("\n💡 部署建议:")
    print("   1. 先用S5.4XLARGE32测试验证 (1-2周)")
    print("   2. 确认无误后升级到S5.8XLARGE64")
    print("   3. 购买1年预留实例，节省40%费用")
    print("   4. 配置监控和自动伸缩")
    
    print("\n📞 如需进一步咨询，建议联系对应云服务商获取详细报价和技术支持。")

if __name__ == "__main__":
    main()