import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Tuple, Optional
import streamlit as st
import asyncio

# 导入包内的模块
from .utils import safe_json_convert
from .technical_analysis import TechnicalAnalyzer
from .ai_recommendation import AIRecommendationEngine
from .kdas_analysis import KDASAnalyzer
from .data_handler import DataHandler

"""
KDAS智能分析系统 - 使用说明

这个模块提供了一个完整的KDAS（Key Date Average Settlement）智能分析系统，
能够根据证券类型和代码自动进行日期推荐和状态分析。

主要功能：
1. 自动获取证券数据（股票、ETF）
2. AI智能推荐KDAS关键日期
3. 计算KDAS指标
4. 分析当前KDAS交易状态
5. 支持单个和批量分析

快速开始：

# 单个证券分析
from kdas_ai_advisor import analyze_security_kdas
import asyncio

async def main():
    result = await analyze_security_kdas(
        security_type="股票",  # 或 "ETF"
        symbol="000001",      # 证券代码
        api_key="your-api-key",
        model="deepseek-r1"   # 可选，默认为deepseek-r1
    )
    
    if result['success']:
        print("推荐日期:", result['recommended_dates'])
        print("分析结果:", result['analysis']['analysis'])
    else:
        print("分析失败:", result['error'])

asyncio.run(main())

# 批量分析
from kdas_ai_advisor import batch_analyze_securities

async def batch_main():
    securities = [
        {"security_type": "股票", "symbol": "000001"},
        {"security_type": "ETF", "symbol": "159915"}
    ]
    
    results = await batch_analyze_securities(securities, "your-api-key")
    for result in results:
        if result['success']:
            print(f"{result['security_info']['name']}: {result['recommended_dates']}")

asyncio.run(batch_main())

返回结果结构：
{
    'success': True/False,
    'security_info': {
        'symbol': '证券代码',
        'name': '证券名称', 
        'type': '证券类型'
    },
    'recommended_dates': ['2024-01-01', '2024-02-01', ...],  # AI推荐的5个日期
    'input_dates': {'day1': '20240101', ...},  # 用于KDAS计算的日期格式
    'recommendation': {  # 日期推荐详情
        'success': True,
        'dates': [...],
        'reasoning': '推荐理由',
        'confidence': 'high/medium/low'
    },
    'analysis': {  # KDAS状态分析
        'success': True,
        'analysis': 'JSON格式的详细分析结果'
    },
    'data_summary': {
        'total_records': 数据条数,
        'date_range': '数据时间范围',
        'current_price': 当前价格
    }
}

注意事项：
1. 需要有效的AI API密钥
2. 需要安装akshare库用于获取证券数据
3. 首次运行会下载证券基础信息，可能需要一些时间
4. 支持的证券类型：股票、ETF
5. 所有函数都是异步的，需要使用await调用
"""


class KDASAIAdvisor:
    """KDAS智能顾问 - 基于AI的日期推荐和状态分析系统"""
    
    def __init__(self, api_key: str = None, model: str = "deepseek-r1"):
        """
        初始化KDAS智能顾问
        
        Args:
            api_key: AI API密钥
            model: 要使用的AI模型名称
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', 'sk-OI98X2iylUhYtncA518f4c7dEa0746A290D590B90c941d01')
        self.model = model
        
        # 初始化各个组件
        self.data_handler = DataHandler()
        self.technical_analyzer = TechnicalAnalyzer()
        self.ai_engine = AIRecommendationEngine(api_key=self.api_key, model=self.model)
        self.kdas_analyzer = KDASAnalyzer(api_key=self.api_key, model=self.model)

    async def analyze_all_async(self, security_type: str, symbol: str, api_key: str, model: str = "deepseek-r1") -> Dict:
        """
        根据证券类型和代码自动进行完整的KDAS分析
        
        Args:
            security_type: 证券类型 ("股票" 或 "ETF")
            symbol: 证券代码
            api_key: AI API密钥
            model: AI模型名称，默认为"deepseek-r1"
            
        Returns:
            包含推荐日期和分析结果的字典
        """
        # 更新API密钥和模型
        self.api_key = api_key
        self.model = model
        self.ai_engine.api_key = api_key
        self.ai_engine.model = model
        self.kdas_analyzer.api_key = api_key
        self.kdas_analyzer.model = model
        
        # 重新初始化AI组件的客户端
        if self.api_key:
            from openai import OpenAI, AsyncOpenAI
            self.ai_engine.client = OpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
            self.ai_engine.async_client = AsyncOpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
            self.kdas_analyzer.client = OpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
            self.kdas_analyzer.async_client = AsyncOpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
        else:
            return {
                'success': False,
                'error': 'AI API密钥未配置',
                'recommendation': None,
                'analysis': None
            }
        
        try:
            # 1. 获取证券信息
            security_name = self.data_handler.get_security_name(symbol, security_type)
            
            # 2. 获取证券数据 - 使用默认的时间范围
            default_dates = self.data_handler.generate_default_dates()
            df = self.data_handler.get_security_data(symbol, default_dates, security_type)
            
            if df.empty:
                return {
                    'success': False,
                    'error': f'未找到该{security_type}的数据，请检查{security_type}代码是否正确',
                    'recommendation': None,
                    'analysis': None
                }
            
            # 3. 先进行日期推荐
            recommendation_result = await self.ai_engine.generate_kdas_recommendation_async(
                df, symbol, security_name, security_type
            )
            
            if not recommendation_result.get('success', False):
                return {
                    'success': False,
                    'error': f'日期推荐失败: {recommendation_result.get("error", "未知错误")}',
                    'recommendation': recommendation_result,
                    'analysis': None
                }
            
            # 4. 使用推荐的日期计算KDAS
            recommended_dates = recommendation_result.get('dates', [])
            if not recommended_dates:
                return {
                    'success': False,
                    'error': '未获得有效的推荐日期',
                    'recommendation': recommendation_result,
                    'analysis': None
                }
            
            # 转换日期格式为KDAS计算所需的格式
            input_dates = self.data_handler.format_dates_for_kdas(recommended_dates)
            
            # 重新获取数据以确保包含推荐日期的范围
            df_with_kdas = self.data_handler.get_security_data(symbol, input_dates, security_type)
            
            if df_with_kdas.empty:
                return {
                    'success': False,
                    'error': '重新获取数据失败',
                    'recommendation': recommendation_result,
                    'analysis': None
                }
            
            # 5. 计算KDAS
            df_processed = self.data_handler.calculate_cumulative_vwap(df_with_kdas, input_dates)
            
            # 6. 进行KDAS状态分析
            analysis_result = await self.kdas_analyzer.analyze_kdas_state_async(
                df_processed, input_dates, symbol, security_name, security_type
            )
            
            # 7. 获取数据摘要
            data_summary = self.data_handler.get_data_summary(df_processed)
            
            return {
                'success': True,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'security_info': {
                    'symbol': symbol,
                    'name': security_name,
                    'type': security_type
                },
                'recommended_dates': recommended_dates,
                'input_dates': input_dates,
                'recommendation': recommendation_result,
                'analysis': analysis_result,
                'data_summary': data_summary
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'完整分析失败: {str(e)}',
                'recommendation': None,
                'analysis': None
            }

    async def batch_analyze_securities_async(self, securities_list: List[Dict], api_key: str, model: str = "deepseek-r1") -> List[Dict]:
        """
        批量异步分析多个证券
        
        Args:
            securities_list: 证券列表，每个元素包含：
                - security_type: str ("股票" 或 "ETF")
                - symbol: str (证券代码)
            api_key: AI API密钥
            model: AI模型名称，默认为"deepseek-r1"
                
        Returns:
            包含所有证券分析结果的列表
        """
        try:
            # 为每个证券创建分析任务
            tasks = []
            for security_info in securities_list:
                task = self.analyze_all_async(
                    security_type=security_info['security_type'],
                    symbol=security_info['symbol'],
                    api_key=api_key,
                    model=model
                )
                tasks.append((security_info['symbol'], task))
            
            # 并发执行所有任务
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # 组织结果
            final_results = []
            for i, (symbol, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    final_results.append({
                        'success': False,
                        'error': f'证券{symbol}分析失败: {str(result)}',
                        'symbol': symbol,
                        'recommendation': None,
                        'analysis': None
                    })
                else:
                    final_results.append(result)
            
            return final_results
            
        except Exception as e:
            return [{
                'success': False,
                'error': f'批量分析失败: {str(e)}',
                'symbol': security.get('symbol', '未知'),
                'recommendation': None,
                'analysis': None
            } for security in securities_list]


# 便捷使用函数
async def analyze_security_kdas(security_type: str, symbol: str, api_key: str, model: str = "deepseek-r1") -> Dict:
    """
    便捷的证券KDAS分析函数
    
    Args:
        security_type: 证券类型 ("股票" 或 "ETF")
        symbol: 证券代码
        api_key: AI API密钥
        model: AI模型名称，默认为"deepseek-r1"
        
    Returns:
        包含推荐日期和分析结果的字典
        
    Example:
        # 分析单个股票
        result = await analyze_security_kdas("股票", "000001", "your-api-key")
        
        # 分析ETF
        result = await analyze_security_kdas("ETF", "159915", "your-api-key", "gpt-4")
    """
    advisor = KDASAIAdvisor()
    return await advisor.analyze_all_async(security_type, symbol, api_key, model)

async def batch_analyze_securities(securities_list: List[Dict], api_key: str, model: str = "deepseek-r1") -> List[Dict]:
    """
    批量分析多个证券的便捷函数
    
    Args:
        securities_list: 证券列表，每个元素包含：
            - security_type: str ("股票" 或 "ETF")
            - symbol: str (证券代码)
        api_key: AI API密钥
        model: AI模型名称，默认为"deepseek-r1"
        
    Returns:
        包含所有证券分析结果的列表
        
    Example:
        securities = [
            {"security_type": "股票", "symbol": "000001"},
            {"security_type": "ETF", "symbol": "159915"},
            {"security_type": "股票", "symbol": "000858"}
        ]
        results = await batch_analyze_securities(securities, "your-api-key")
    """
    advisor = KDASAIAdvisor()
    return await advisor.batch_analyze_securities_async(securities_list, api_key, model)

def get_ai_advisor(api_key: str = None, model: str = "deepseek-r1") -> Optional[KDASAIAdvisor]:
    """获取KDAS AI顾问实例"""
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            # 尝试从Streamlit secrets获取
            try:
                if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
                    api_key = st.secrets['OPENAI_API_KEY']
            except:
                pass
    
    # 即使没有API密钥也返回实例，用于测试和展示
    return KDASAIAdvisor(api_key, model)