"""
KDAS AI顾问异步功能使用示例

此文件展示了如何使用新增的异步方法来提升KDAS分析的效率。
异步方法特别适用于需要同时分析多个证券或者执行多个AI任务的场景。
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from kdas_ai_advisor import get_ai_advisor

async def example_single_security_async():
    """单个证券的异步分析示例"""
    print("🚀 单个证券异步分析示例")
    print("=" * 50)
    
    # 初始化AI顾问
    advisor = get_ai_advisor(api_key="your-api-key-here", model="deepseek-r1")
    
    # 模拟证券数据（实际使用中应该从KDAS.py的get_security_data获取）
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    sample_data = pd.DataFrame({
        '日期': dates,
        '开盘': [100 + i*0.1 for i in range(len(dates))],
        '收盘': [100.5 + i*0.1 for i in range(len(dates))],
        '最高': [101 + i*0.1 for i in range(len(dates))],
        '最低': [99.5 + i*0.1 for i in range(len(dates))],
        '成交量': [1000000 + i*1000 for i in range(len(dates))],
        '成交额': [100000000 + i*100000 for i in range(len(dates))]
    })
    
    # 示例日期配置
    input_dates = {
        'day1': '20240924',
        'day2': '20241107', 
        'day3': '20241217',
        'day4': '20250407',
        'day5': '20250423'
    }
    
    try:
        print("⏰ 开始异步分析...")
        start_time = datetime.now()
        
        # 使用analyze_all_async方法同时进行日期推荐和状态分析
        result = await advisor.analyze_all_async(
            df=sample_data,
            symbol="000001",
            security_name="平安银行", 
            security_type="股票",
            input_dates=input_dates
        )
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"✅ 分析完成，耗时: {elapsed:.2f}秒")
        print(f"📊 推荐成功: {result['recommendation']['success'] if result['recommendation'] else False}")
        print(f"🧠 分析成功: {result['analysis']['success'] if result['analysis'] else False}")
        
        if result['recommendation'] and result['recommendation']['success']:
            print(f"📅 推荐日期: {result['recommendation']['dates']}")
        
        if result['analysis'] and result['analysis']['success']:
            print(f"🔍 分析完成时间: {result['analysis']['timestamp']}")
            
    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")

async def example_batch_analysis_async():
    """批量证券异步分析示例"""
    print("\n🚀 批量证券异步分析示例")
    print("=" * 50)
    
    # 初始化AI顾问
    advisor = get_ai_advisor(api_key="your-api-key-here", model="deepseek-r1")
    
    # 模拟多个证券的数据
    securities_data = []
    
    securities_info = [
        ("000001", "平安银行", "股票"),
        ("159915", "创业板ETF", "ETF"),
        ("000300", "沪深300", "指数")
    ]
    
    for symbol, name, sec_type in securities_info:
        # 为每个证券创建模拟数据
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        sample_data = pd.DataFrame({
            '日期': dates,
            '开盘': [100 + i*0.1 for i in range(len(dates))],
            '收盘': [100.5 + i*0.1 for i in range(len(dates))],
            '最高': [101 + i*0.1 for i in range(len(dates))],
            '最低': [99.5 + i*0.1 for i in range(len(dates))],
            '成交量': [1000000 + i*1000 for i in range(len(dates))],
            '成交额': [100000000 + i*100000 for i in range(len(dates))]
        })
        
        input_dates = {
            'day1': '20240924',
            'day2': '20241107', 
            'day3': '20241217',
            'day4': '20250407',
            'day5': '20250423'
        }
        
        securities_data.append({
            'df': sample_data,
            'symbol': symbol,
            'security_name': name,
            'security_type': sec_type,
            'input_dates': input_dates
        })
    
    try:
        print(f"⏰ 开始批量分析 {len(securities_data)} 个证券...")
        start_time = datetime.now()
        
        # 使用batch_analyze_securities_async方法批量分析
        results = await advisor.batch_analyze_securities_async(securities_data)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"✅ 批量分析完成，总耗时: {elapsed:.2f}秒")
        print(f"📊 平均每个证券耗时: {elapsed/len(securities_data):.2f}秒")
        
        # 显示结果摘要
        for result in results:
            symbol = result.get('symbol', '未知')
            success = result.get('success', False)
            print(f"  - {symbol}: {'✅ 成功' if success else '❌ 失败'}")
            
    except Exception as e:
        print(f"❌ 批量分析失败: {str(e)}")

async def example_performance_comparison():
    """性能对比示例：同步 vs 异步"""
    print("\n🚀 性能对比示例：同步 vs 异步")
    print("=" * 50)
    
    advisor = get_ai_advisor(api_key="your-api-key-here", model="deepseek-r1")
    
    # 准备测试数据
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    sample_data = pd.DataFrame({
        '日期': dates,
        '开盘': [100 + i*0.1 for i in range(len(dates))],
        '收盘': [100.5 + i*0.1 for i in range(len(dates))],
        '最高': [101 + i*0.1 for i in range(len(dates))],
        '最低': [99.5 + i*0.1 for i in range(len(dates))],
        '成交量': [1000000 + i*1000 for i in range(len(dates))],
        '成交额': [100000000 + i*100000 for i in range(len(dates))]
    })
    
    input_dates = {
        'day1': '20240924',
        'day2': '20241107', 
        'day3': '20241217',
        'day4': '20250407',
        'day5': '20250423'
    }
    
    try:
        # 同步方式：顺序执行
        print("⏰ 同步方式测试...")
        sync_start = datetime.now()
        
        recommendation_result = advisor.generate_kdas_recommendation(
            sample_data, "000001", "平安银行", "股票"
        )
        analysis_result = advisor.analyze_kdas_state(
            sample_data, input_dates, "000001", "平安银行", "股票"
        )
        
        sync_end = datetime.now()
        sync_elapsed = (sync_end - sync_start).total_seconds()
        
        print(f"📊 同步方式耗时: {sync_elapsed:.2f}秒")
        
        # 异步方式：并发执行
        print("⏰ 异步方式测试...")
        async_start = datetime.now()
        
        async_result = await advisor.analyze_all_async(
            sample_data, "000001", "平安银行", "股票", input_dates
        )
        
        async_end = datetime.now() 
        async_elapsed = (async_end - async_start).total_seconds()
        
        print(f"🚀 异步方式耗时: {async_elapsed:.2f}秒")
        print(f"⚡ 性能提升: {((sync_elapsed - async_elapsed) / sync_elapsed * 100):.1f}%")
        
    except Exception as e:
        print(f"❌ 性能测试失败: {str(e)}")

async def main():
    """主函数，运行所有示例"""
    print("🤖 KDAS AI顾问异步功能演示")
    print("=" * 60)
    
    # 注意：这些示例需要有效的API密钥才能正常运行
    # 请将 "your-api-key-here" 替换为您的实际API密钥
    
    await example_single_security_async()
    await example_batch_analysis_async()
    await example_performance_comparison()
    
    print("\n🎉 所有示例演示完成！")
    print("\n💡 使用提示：")
    print("1. 异步方法特别适用于需要同时处理多个证券的场景")
    print("2. 在多图看板中使用批量异步分析可以显著提升加载速度")
    print("3. 单个证券分析时，异步方法可以同时进行日期推荐和状态分析")
    print("4. 记得在调用异步方法时使用 await 关键字")
    print("5. 需要在异步环境中运行，可以使用 asyncio.run()")

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main()) 