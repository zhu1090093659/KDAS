#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KDAS智能分析系统测试脚本

这个脚本用于测试新的KDAS分析功能，包括：
1. 单个证券分析
2. 批量证券分析
3. 错误处理测试

使用方法：
python test_kdas_advisor.py
"""

import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from utils.kdas_ai_advisor import analyze_security_kdas, batch_analyze_securities

async def test_single_security():
    """测试单个证券分析"""
    print("🧪 测试单个证券分析")
    print("-" * 40)
    
    # 使用测试API密钥（请替换为真实的API密钥）
    test_api_key = "sk-test-key-here"  # 请替换为您的实际API密钥
    
    try:
        # 测试股票分析
        print("正在测试股票分析 (000001 平安银行)...")
        result = await analyze_security_kdas(
            security_type="股票",
            symbol="000001",
            api_key=test_api_key,
            model="deepseek-r1"
        )
        
        print(f"分析结果: {'成功' if result['success'] else '失败'}")
        if result['success']:
            print(f"证券名称: {result['security_info']['name']}")
            print(f"推荐日期: {result['recommended_dates']}")
            print(f"数据范围: {result['data_summary']['date_range']}")
            print(f"当前价格: ¥{result['data_summary']['current_price']:.3f}")
        else:
            print(f"错误信息: {result['error']}")
            
    except Exception as e:
        print(f"测试异常: {str(e)}")
    
    print()

async def test_batch_analysis():
    """测试批量分析"""
    print("🧪 测试批量证券分析")
    print("-" * 40)
    
    test_api_key = "sk-test-key-here"  # 请替换为您的实际API密钥
    
    # 测试证券列表
    securities = [
        {"security_type": "股票", "symbol": "000001"},  # 平安银行
        {"security_type": "ETF", "symbol": "159915"},   # 创业板ETF
        {"security_type": "股票", "symbol": "000858"},  # 五粮液
    ]
    
    try:
        print(f"正在批量分析 {len(securities)} 个证券...")
        results = await batch_analyze_securities(securities, test_api_key)
        
        for i, result in enumerate(results):
            security = securities[i]
            print(f"\n{i+1}. {security['security_type']} {security['symbol']}:")
            
            if result['success']:
                print(f"   ✅ 分析成功")
                print(f"   证券名称: {result['security_info']['name']}")
                print(f"   推荐日期数量: {len(result['recommended_dates'])}")
                print(f"   当前价格: ¥{result['data_summary']['current_price']:.3f}")
            else:
                print(f"   ❌ 分析失败: {result['error']}")
                
    except Exception as e:
        print(f"批量测试异常: {str(e)}")
    
    print()

async def test_error_handling():
    """测试错误处理"""
    print("🧪 测试错误处理")
    print("-" * 40)
    
    try:
        # 测试无效API密钥
        print("测试无效API密钥...")
        result = await analyze_security_kdas(
            security_type="股票",
            symbol="000001",
            api_key="invalid-key",
            model="deepseek-r1"
        )
        print(f"结果: {'成功' if result['success'] else '失败 (预期)'}")
        if not result['success']:
            print(f"错误信息: {result['error']}")
        
        # 测试无效证券代码
        print("\n测试无效证券代码...")
        result = await analyze_security_kdas(
            security_type="股票",
            symbol="999999",  # 不存在的代码
            api_key="sk-test-key-here",
            model="deepseek-r1"
        )
        print(f"结果: {'成功' if result['success'] else '失败 (预期)'}")
        if not result['success']:
            print(f"错误信息: {result['error']}")
            
    except Exception as e:
        print(f"错误处理测试异常: {str(e)}")
    
    print()

async def main():
    """主测试函数"""
    print("🚀 KDAS智能分析系统测试")
    print("=" * 50)
    print("注意: 请确保在运行测试前替换为有效的API密钥")
    print("=" * 50)
    
    # 运行所有测试
    await test_single_security()
    await test_batch_analysis()
    await test_error_handling()
    
    print("=" * 50)
    print("✅ 所有测试完成!")
    print("\n使用提示:")
    print("1. 将 'sk-test-key-here' 替换为您的实际API密钥")
    print("2. 确保网络连接正常，能够访问akshare数据源")
    print("3. 首次运行可能需要下载证券基础信息")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main()) 