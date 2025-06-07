"""
KDAS命令行接口

提供简单的命令行工具来使用KDAS分析功能
"""

import argparse
import asyncio
import json
import sys
from typing import List, Dict

from .advisor import analyze_security_kdas, batch_analyze_securities


def print_result(result: Dict):
    """格式化打印分析结果"""
    if result['success']:
        print(f"\n=== {result['security_info']['name']} ({result['security_info']['symbol']}) ===")
        print(f"证券类型: {result['security_info']['type']}")
        print(f"当前价格: ¥{result['data_summary']['current_price']:.3f}")
        print(f"数据范围: {result['data_summary']['date_range']}")
        
        print(f"\n推荐日期:")
        for i, date in enumerate(result['recommended_dates'], 1):
            print(f"  {i}. {date}")
        
        if result['recommendation']['success']:
            print(f"\n推荐理由: {result['recommendation']['reasoning'][:200]}...")
            print(f"置信度: {result['recommendation']['confidence']}")
        
        if result['analysis']['success']:
            print(f"\nKDAS分析: {result['analysis']['analysis'][:200]}...")
    else:
        print(f"❌ 分析失败: {result['error']}")


async def analyze_single(args):
    """分析单个证券"""
    print(f"正在分析 {args.type} {args.symbol}...")
    
    result = await analyze_security_kdas(
        security_type=args.type,
        symbol=args.symbol,
        api_key=args.api_key,
        model=args.model
    )
    
    print_result(result)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")


async def analyze_batch(args):
    """批量分析证券"""
    securities = []
    
    # 从文件读取证券列表
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    securities = data
                else:
                    print("❌ 文件格式错误，应该是包含证券信息的JSON数组")
                    return
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return
    else:
        # 从命令行参数构建
        securities = [{"security_type": args.type, "symbol": args.symbol}]
    
    print(f"正在批量分析 {len(securities)} 个证券...")
    
    results = await batch_analyze_securities(securities, args.api_key, args.model)
    
    success_count = 0
    for result in results:
        print_result(result)
        if result['success']:
            success_count += 1
        print("-" * 50)
    
    print(f"\n批量分析完成: {success_count}/{len(results)} 成功")
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {args.output}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="KDAS智能分析系统命令行工具")
    
    # 全局参数
    parser.add_argument("--api-key", required=True, help="AI API密钥")
    parser.add_argument("--model", default="deepseek-r1", help="AI模型名称 (默认: deepseek-r1)")
    parser.add_argument("--output", "-o", help="输出文件路径")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 单个分析命令
    single_parser = subparsers.add_parser("analyze", help="分析单个证券")
    single_parser.add_argument("type", choices=["股票", "ETF"], help="证券类型")
    single_parser.add_argument("symbol", help="证券代码")
    
    # 批量分析命令
    batch_parser = subparsers.add_parser("batch", help="批量分析证券")
    batch_parser.add_argument("--file", "-f", help="包含证券列表的JSON文件")
    batch_parser.add_argument("--type", choices=["股票", "ETF"], help="证券类型 (当不使用文件时)")
    batch_parser.add_argument("--symbol", help="证券代码 (当不使用文件时)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "analyze":
            asyncio.run(analyze_single(args))
        elif args.command == "batch":
            asyncio.run(analyze_batch(args))
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 