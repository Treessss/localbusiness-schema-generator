#!/usr/bin/env python3
"""测试运行脚本"""

import sys
import subprocess
import os
from pathlib import Path


def run_tests():
    """运行测试套件"""
    # 确保在项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print("🧪 开始运行测试套件...")
    print(f"📁 项目目录: {project_root}")
    
    # 检查是否安装了测试依赖
    try:
        import pytest
        import jsonschema
    except ImportError as e:
        print(f"❌ 缺少测试依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return 1
    
    # 运行测试命令
    test_commands = [
        # 运行所有测试
        ["python", "-m", "pytest", "tests/", "-v"],
        
        # 只运行 API 测试
        # ["python", "-m", "pytest", "tests/test_api_extract.py", "-v"],
        
        # 只运行响应格式测试
        # ["python", "-m", "pytest", "tests/test_response_format.py", "-v"],
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n🔄 运行测试命令 {i}/{len(test_commands)}: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ 测试命令 {i} 执行成功")
                print(result.stdout)
            else:
                print(f"❌ 测试命令 {i} 执行失败")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return result.returncode
                
        except Exception as e:
            print(f"❌ 执行测试时出错: {e}")
            return 1
    
    print("\n🎉 所有测试执行完成！")
    return 0


def run_specific_test(test_file=None, test_function=None):
    """运行特定测试"""
    cmd = ["python", "-m", "pytest", "-v"]
    
    if test_file:
        cmd.append(f"tests/{test_file}")
        
    if test_function:
        if test_file:
            cmd[-1] += f"::{test_function}"
        else:
            cmd.extend(["-k", test_function])
    
    print(f"🔄 运行特定测试: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd)
        return result.returncode
    except Exception as e:
        print(f"❌ 执行测试时出错: {e}")
        return 1


def show_help():
    """显示帮助信息"""
    print("""
🧪 测试运行脚本使用说明

用法:
    python run_tests.py                    # 运行所有测试
    python run_tests.py --file <文件名>     # 运行特定测试文件
    python run_tests.py --func <函数名>     # 运行特定测试函数
    python run_tests.py --help             # 显示此帮助信息

示例:
    python run_tests.py --file test_api_extract.py
    python run_tests.py --func test_extract_success_response_format
    python run_tests.py --file test_response_format.py --func test_success_response_structure

测试文件:
    - test_api_extract.py: 测试 /api/extract 接口功能
    - test_response_format.py: 测试响应格式验证
    """)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="运行测试套件")
    parser.add_argument("--file", help="指定测试文件名")
    parser.add_argument("--func", help="指定测试函数名")
    parser.add_argument("--help-tests", action="store_true", help="显示测试帮助信息")
    
    args = parser.parse_args()
    
    if args.help_tests:
        show_help()
        sys.exit(0)
    
    if args.file or args.func:
        exit_code = run_specific_test(args.file, args.func)
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)