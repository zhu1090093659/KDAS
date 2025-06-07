from openai import OpenAI, AsyncOpenAI
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Tuple, Optional
import streamlit as st
import asyncio

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

def safe_json_convert(obj):
    """安全地转换数据类型以支持JSON序列化"""
    if isinstance(obj, dict):
        return {k: safe_json_convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_convert(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj

class KDASAIAdvisor:
    """KDAS智能顾问 - 基于GPT-4o的日期推荐系统"""
    
    def __init__(self, api_key: str = None, model: str = "deepseek-r1"):
        """
        初始化KDAS智能顾问
        
        Args:
            api_key: AI API密钥
            model: 要使用的AI模型名称
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', 'sk-OI98X2iylUhYtncA518f4c7dEa0746A290D590B90c941d01')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
            self.async_client = AsyncOpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
        else:
            self.client = None
            self.async_client = None
        self.model = model  # 用户选择的AI模型
        
    def analyze_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """
        分析技术指标和关键价格点
        
        Args:
            df: 包含价格和成交量数据的DataFrame
            
        Returns:
            包含技术分析结果的字典
        """
        if df.empty:
            return {}
            
        # 确保数据按日期排序
        df = df.sort_values('日期').reset_index(drop=True)
        
        # 计算技术指标
        analysis = {}
        
        # 1. 价格统计信息
        analysis['price_stats'] = {
            'current_price': float(df['收盘'].iloc[-1]),
            'max_price': float(df['最高'].max()),
            'min_price': float(df['最低'].min()),
            'avg_price': float(df['收盘'].mean()),
            'price_volatility': float(df['收盘'].std())
        }
        
        # 2. 成交量分析
        recent_volume = float(df['成交量'].tail(10).mean())
        early_volume = float(df['成交量'].head(-10).mean()) if len(df) > 10 else float(df['成交量'].mean())
        
        analysis['volume_stats'] = {
            'avg_volume': float(df['成交量'].mean()),
            'max_volume': float(df['成交量'].max()),
            'recent_avg_volume': float(df['成交量'].tail(20).mean()),
            'volume_trend': 'increasing' if recent_volume > early_volume else 'decreasing'
        }
        
        # 3. 识别重要的价格转折点
        analysis['key_levels'] = self._find_key_price_levels(df)
        
        # 4. 识别异常成交量日期
        analysis['volume_spikes'] = self._find_volume_spikes(df)
        
        # 5. 趋势分析
        analysis['trend_analysis'] = self._analyze_trends(df)
        
        # 6. 支撑阻力位分析
        analysis['support_resistance'] = self._find_support_resistance(df)
        
        # 确保所有数据都是JSON可序列化的
        return safe_json_convert(analysis)
    
    def _find_key_price_levels(self, df: pd.DataFrame) -> List[Dict]:
        """寻找关键价格水平（高点、低点）"""
        key_levels = []
        
        # 寻找局部高点和低点
        high_points = self._find_local_extrema(df['最高'], is_high=True)
        low_points = self._find_local_extrema(df['最低'], is_high=False)
        
        # 添加显著的高点
        for idx in high_points[-10:]:  # 最近10个高点
            if idx < len(df):
                key_levels.append({
                    'date': df.iloc[idx]['日期'].strftime('%Y-%m-%d'),
                    'price': float(df.iloc[idx]['最高']),
                    'type': 'high',
                    'volume': float(df.iloc[idx]['成交量'])
                })
        
        # 添加显著的低点
        for idx in low_points[-10:]:  # 最近10个低点
            if idx < len(df):
                key_levels.append({
                    'date': df.iloc[idx]['日期'].strftime('%Y-%m-%d'),
                    'price': float(df.iloc[idx]['最低']),
                    'type': 'low',
                    'volume': float(df.iloc[idx]['成交量'])
                })
        
        # 按日期排序
        key_levels.sort(key=lambda x: x['date'])
        
        return safe_json_convert(key_levels)
    
    def _find_local_extrema(self, series: pd.Series, is_high: bool = True, window: int = 5) -> List[int]:
        """寻找局部极值点"""
        extrema = []
        
        for i in range(window, len(series) - window):
            if is_high:
                # 寻找局部最高点
                if all(series.iloc[i] >= series.iloc[j] for j in range(i-window, i+window+1) if j != i):
                    extrema.append(i)
            else:
                # 寻找局部最低点
                if all(series.iloc[i] <= series.iloc[j] for j in range(i-window, i+window+1) if j != i):
                    extrema.append(i)
        
        return extrema
    
    def _find_volume_spikes(self, df: pd.DataFrame, threshold_multiplier: float = 2.0) -> List[Dict]:
        """寻找成交量异常放大的日期"""
        avg_volume = df['成交量'].rolling(window=20, min_periods=1).mean()
        volume_spikes = []
        
        for i, row in df.iterrows():
            if row['成交量'] > avg_volume.iloc[i] * threshold_multiplier:
                volume_spikes.append({
                    'date': row['日期'].strftime('%Y-%m-%d'),
                    'volume': float(row['成交量']),
                    'avg_volume': float(avg_volume.iloc[i]),
                    'multiplier': float(row['成交量'] / avg_volume.iloc[i]),
                    'price': float(row['收盘'])
                })
        
        # 只返回最显著的成交量异常
        volume_spikes.sort(key=lambda x: x['multiplier'], reverse=True)
        return safe_json_convert(volume_spikes[:15])  # 最多返回15个
    
    def _analyze_trends(self, df: pd.DataFrame) -> Dict:
        """分析价格趋势"""
        # 计算不同周期的移动平均线
        df_temp = df.copy()
        df_temp['MA5'] = df_temp['收盘'].rolling(window=5).mean()
        df_temp['MA10'] = df_temp['收盘'].rolling(window=10).mean()
        df_temp['MA20'] = df_temp['收盘'].rolling(window=20).mean()
        df_temp['MA60'] = df_temp['收盘'].rolling(window=60).mean()
        
        current_price = df_temp['收盘'].iloc[-1]
        
        # 确保布尔值转换为Python原生bool类型
        ma5_valid = not pd.isna(df_temp['MA5'].iloc[-1]) if len(df_temp) > 0 else False
        ma20_valid = not pd.isna(df_temp['MA20'].iloc[-1]) if len(df_temp) > 0 else False  
        ma60_valid = not pd.isna(df_temp['MA60'].iloc[-1]) if len(df_temp) > 0 else False
        
        trend_analysis = {
            'short_term': 'neutral',  # 5日均线趋势
            'medium_term': 'neutral',  # 20日均线趋势  
            'long_term': 'neutral',   # 60日均线趋势
            'ma_positions': {
                'above_ma5': bool(current_price > df_temp['MA5'].iloc[-1]) if ma5_valid else False,
                'above_ma20': bool(current_price > df_temp['MA20'].iloc[-1]) if ma20_valid else False,
                'above_ma60': bool(current_price > df_temp['MA60'].iloc[-1]) if ma60_valid else False
            }
        }
        
        # 判断趋势方向
        if len(df_temp) >= 5:
            ma5_trend = df_temp['MA5'].iloc[-1] - df_temp['MA5'].iloc[-5] if not pd.isna(df_temp['MA5'].iloc[-1]) else 0
            trend_analysis['short_term'] = 'bullish' if ma5_trend > 0 else 'bearish'
        
        if len(df_temp) >= 20:
            ma20_trend = df_temp['MA20'].iloc[-1] - df_temp['MA20'].iloc[-20] if not pd.isna(df_temp['MA20'].iloc[-1]) else 0
            trend_analysis['medium_term'] = 'bullish' if ma20_trend > 0 else 'bearish'
        
        if len(df_temp) >= 60:
            ma60_trend = df_temp['MA60'].iloc[-1] - df_temp['MA60'].iloc[-60] if not pd.isna(df_temp['MA60'].iloc[-1]) else 0
            trend_analysis['long_term'] = 'bullish' if ma60_trend > 0 else 'bearish'
        
        return safe_json_convert(trend_analysis)
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Dict:
        """寻找支撑位和阻力位"""
        # 简化的支撑阻力位识别
        recent_data = df.tail(60)  # 最近60个交易日
        
        # 计算价格分布
        price_levels = []
        for _, row in recent_data.iterrows():
            price_levels.extend([row['最高'], row['最低'], row['收盘']])
        
        # 使用价格聚类来识别支撑阻力位
        price_levels = sorted(price_levels)
        current_price = df['收盘'].iloc[-1]
        
        support_levels = [p for p in price_levels if p < current_price][-5:]  # 最近5个支撑位
        resistance_levels = [p for p in price_levels if p > current_price][:5]  # 最近5个阻力位
        
        result = {
            'support_levels': [float(level) for level in support_levels],
            'resistance_levels': [float(level) for level in resistance_levels],
            'current_price': float(current_price)
        }
        return safe_json_convert(result)
    
    def generate_kdas_recommendation(self, df: pd.DataFrame, symbol: str, security_name: str, security_type: str) -> Dict:
        """
        生成KDAS日期推荐
        
        Args:
            df: 价格数据DataFrame
            symbol: 证券代码
            security_name: 证券名称
            security_type: 证券类型
            
        Returns:
            包含推荐日期和理由的字典
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'AI API密钥未配置',
                'fallback_dates': self._generate_fallback_dates(df)
            }
        
        try:
            # 分析技术数据
            technical_analysis = self.analyze_technical_indicators(df)
            
            # 准备发送给GPT的数据
            gpt_input = self._prepare_gpt_input(df, technical_analysis, symbol, security_name, security_type)
            
            # 调用大语言模型
            response = self._call_llm(gpt_input)
            
            # 解析llm回复
            recommendation = self._parse_gpt_response(response)
            
            # 验证推荐日期的有效性
            validated_dates = self._validate_recommended_dates(recommendation['dates'], df)
            
            return {
                'success': True,
                'dates': validated_dates,
                'reasoning': recommendation['reasoning'],
                'confidence': recommendation.get('confidence', 'medium'),
                'technical_analysis': technical_analysis
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'GPT调用失败: {str(e)}',
                'fallback_dates': self._generate_fallback_dates(df)
            }

    async def generate_kdas_recommendation_async(self, df: pd.DataFrame, symbol: str, security_name: str, security_type: str) -> Dict:
        """
        异步生成KDAS日期推荐
        
        Args:
            df: 价格数据DataFrame
            symbol: 证券代码
            security_name: 证券名称
            security_type: 证券类型
            
        Returns:
            包含推荐日期和理由的字典
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'AI API密钥未配置',
                'fallback_dates': self._generate_fallback_dates(df)
            }
        
        try:
            # 分析技术数据
            technical_analysis = self.analyze_technical_indicators(df)
            
            # 准备发送给GPT的数据
            gpt_input = self._prepare_gpt_input(df, technical_analysis, symbol, security_name, security_type)
            
            # 异步调用大语言模型
            response = await self._call_llm_async(gpt_input)
            
            # 解析llm回复
            recommendation = self._parse_gpt_response(response)
            
            # 验证推荐日期的有效性
            validated_dates = self._validate_recommended_dates(recommendation['dates'], df)
            
            return {
                'success': True,
                'dates': validated_dates,
                'reasoning': recommendation['reasoning'],
                'confidence': recommendation.get('confidence', 'medium'),
                'technical_analysis': technical_analysis
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'异步GPT调用失败: {str(e)}',
                'fallback_dates': self._generate_fallback_dates(df)
            }
    
    def _prepare_gpt_input(self, df: pd.DataFrame, technical_analysis: Dict, symbol: str, security_name: str, security_type: str) -> str:
        """准备发送给GPT的输入数据"""
        
        # 获取最近的价格数据摘要
        recent_data = df.tail(30)
        price_summary = {
            'recent_high': float(recent_data['最高'].max()),
            'recent_low': float(recent_data['最低'].min()),
            'current_price': float(df['收盘'].iloc[-1]),
            'data_start_date': df['日期'].iloc[0].strftime('%Y-%m-%d'),
            'data_end_date': df['日期'].iloc[-1].strftime('%Y-%m-%d'),
            'total_days': len(df)
        }
        
        prompt = f"""
你是一位专业的股票技术分析师，精通KDAS（Key Date Average Settlement）交易体系。现在需要为{security_type} {security_name}({symbol}) 推荐5个最佳的KDAS计算起始日期。

KDAS体系原理：
- KDAS是从特定关键日期开始计算的累计成交量加权平均价格
- 关键日期通常选择重要的技术转折点、突破点、或者市场情绪转换点
- 好的KDAS日期应该能够反映出重要的支撑阻力位和趋势变化

证券基本信息：
- 证券名称: {security_name}
- 证券代码: {symbol}
- 证券类型: {security_type}
- 当前价格: {price_summary['current_price']:.3f}元
- 数据范围: {price_summary['data_start_date']} 至 {price_summary['data_end_date']}
- 最近高点: {price_summary['recent_high']:.3f}元
- 最近低点: {price_summary['recent_low']:.3f}元

技术分析数据：
{json.dumps(technical_analysis, ensure_ascii=False, indent=2)}

请基于以上数据分析，推荐5个最佳的KDAS起始日期。要求：

1. 日期必须在数据范围内（{price_summary['data_start_date']} 至 {price_summary['data_end_date']}）
2. 优先选择以下类型的关键日期：
   - 重要的价格突破点
   - 明显的趋势转折点
   - 异常成交量放大的日期
   - 重要的支撑或阻力位形成点
   - 市场情绪明显转换的时点

3. 日期之间要有适当的时间间隔，避免过于集中

请按以下JSON格式回复：
{{
    "dates": [
        "YYYY-MM-DD",
        "YYYY-MM-DD", 
        "YYYY-MM-DD",
        "YYYY-MM-DD",
        "YYYY-MM-DD"
    ],
    "reasoning": "详细说明每个日期选择的理由和技术依据",
    "confidence": "high/medium/low"
}}
"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """调用大语言模型"""
        try:
            if not self.client:
                raise Exception("OpenAI客户端未初始化")
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"你是一位专业的股票技术分析师，精通KDAS交易体系。当前使用的AI模型是{self.model}。请基于技术分析数据给出专业的KDAS日期推荐，确保回复格式严格按照JSON格式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"GPT-4o调用失败: {str(e)}")
    
    async def _call_llm_async(self, prompt: str) -> str:
        """异步调用大语言模型"""
        try:
            if not self.async_client:
                raise Exception("异步OpenAI客户端未初始化")
                
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"你是一位专业的股票技术分析师，精通KDAS交易体系。当前使用的AI模型是{self.model}。请基于技术分析数据给出专业的KDAS日期推荐，确保回复格式严格按照JSON格式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"异步GPT调用失败: {str(e)}")
    
    def _parse_gpt_response(self, response: str) -> Dict:
        """解析GPT回复"""
        try:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                return {
                    'dates': parsed.get('dates', []),
                    'reasoning': parsed.get('reasoning', ''),
                    'confidence': parsed.get('confidence', 'medium')
                }
            else:
                # 如果没有找到JSON，尝试手动解析
                return self._manual_parse_response(response)
                
        except Exception as e:
            raise Exception(f"解析GPT回复失败: {str(e)}")
    
    def _manual_parse_response(self, response: str) -> Dict:
        """手动解析GPT回复"""
        # 简单的备用解析方案
        dates = []
        import re
        
        # 寻找日期格式
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        found_dates = re.findall(date_pattern, response)
        
        # 取前5个日期
        dates = found_dates[:5]
        
        return {
            'dates': dates,
            'reasoning': response,
            'confidence': 'medium'
        }
    
    def _validate_recommended_dates(self, dates: List[str], df: pd.DataFrame) -> List[str]:
        """验证推荐日期的有效性"""
        validated_dates = []
        df_dates = df['日期'].dt.strftime('%Y-%m-%d').tolist()
        
        for date_str in dates:
            try:
                # 检查日期格式
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # 检查日期是否在数据范围内
                if date_str in df_dates:
                    validated_dates.append(date_str)
                else:
                    # 寻找最接近的交易日
                    closest_date = self._find_closest_trading_date(date_str, df_dates)
                    if closest_date:
                        validated_dates.append(closest_date)
                        
            except ValueError:
                continue
        
        # 如果验证后的日期不足5个，用默认日期补充
        if len(validated_dates) < 5:
            fallback_dates = self._generate_fallback_dates(df)
            for fb_date in fallback_dates:
                if fb_date not in validated_dates:
                    validated_dates.append(fb_date)
                if len(validated_dates) >= 5:
                    break
        
        return validated_dates[:5]
    
    def _find_closest_trading_date(self, target_date: str, available_dates: List[str]) -> Optional[str]:
        """寻找最接近的交易日"""
        try:
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            available_dts = [datetime.strptime(d, '%Y-%m-%d') for d in available_dates]
            
            # 寻找最接近的日期
            closest_dt = min(available_dts, key=lambda x: abs((x - target_dt).days))
            
            return closest_dt.strftime('%Y-%m-%d')
        except:
            return None
    
    def _generate_fallback_dates(self, df: pd.DataFrame) -> List[str]:
        """生成备用的KDAS日期（当AI推荐失败时使用）"""
        if df.empty:
            return []
        
        # 基于数据长度生成合理的时间间隔
        total_days = len(df)
        
        if total_days < 30:
            # 数据太少，均匀分布
            indices = np.linspace(0, total_days-1, min(5, total_days), dtype=int)
        else:
            # 选择具有代表性的时间点
            indices = [
                total_days - 1,  # 最新日期
                int(total_days * 0.8),  # 80%位置
                int(total_days * 0.6),  # 60%位置
                int(total_days * 0.3),  # 30%位置
                0  # 最早日期
            ]
        
        fallback_dates = []
        for idx in indices:
            if 0 <= idx < len(df):
                date_str = df.iloc[idx]['日期'].strftime('%Y-%m-%d')
                fallback_dates.append(date_str)
        
        return list(reversed(fallback_dates))  # 按时间顺序排列

    def analyze_kdas_state(self, df: pd.DataFrame, input_dates: Dict, symbol: str, security_name: str, security_type: str) -> Dict:
        """
        分析当前KDAS交易状态
        
        Args:
            df: 包含KDAS计算结果的DataFrame
            input_dates: KDAS计算起始日期字典
            symbol: 证券代码
            security_name: 证券名称
            security_type: 证券类型
            
        Returns:
            包含KDAS状态分析结果的字典
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'AI API密钥未配置',
                'analysis': '需要配置AI API密钥才能使用KDAS状态分析功能'
            }
        
        try:
            # 准备KDAS状态分析数据
            analysis_data = self._prepare_kdas_analysis_data(df, input_dates, symbol, security_name, security_type)
            
            # 准备KDAS分析prompt
            prompt = self._prepare_kdas_analysis_prompt(analysis_data)
            
            # 调用大语言模型进行分析
            response = self._call_llm(prompt)
            
            return {
                'success': True,
                'analysis': response,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'KDAS状态分析失败: {str(e)}',
                'analysis': f'分析过程中出现错误: {str(e)}'
            }

    async def analyze_kdas_state_async(self, df: pd.DataFrame, input_dates: Dict, symbol: str, security_name: str, security_type: str) -> Dict:
        """
        异步分析当前KDAS交易状态
        
        Args:
            df: 包含KDAS计算结果的DataFrame
            input_dates: KDAS计算起始日期字典
            symbol: 证券代码
            security_name: 证券名称
            security_type: 证券类型
            
        Returns:
            包含KDAS状态分析结果的字典
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'AI API密钥未配置',
                'analysis': '需要配置AI API密钥才能使用KDAS状态分析功能'
            }
        
        try:
            # 准备KDAS状态分析数据
            analysis_data = self._prepare_kdas_analysis_data(df, input_dates, symbol, security_name, security_type)
            
            # 准备KDAS分析prompt
            prompt = self._prepare_kdas_analysis_prompt(analysis_data)
            
            # 异步调用大语言模型进行分析
            response = await self._call_llm_async(prompt)
            
            return {
                'success': True,
                'analysis': response,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'异步KDAS状态分析失败: {str(e)}',
                'analysis': f'异步分析过程中出现错误: {str(e)}'
            }

    def _prepare_kdas_analysis_data(self, df: pd.DataFrame, input_dates: Dict, symbol: str, security_name: str, security_type: str) -> Dict:
        """准备KDAS状态分析所需的数据"""
        if df.empty:
            return {}
        
        # 获取最新数据
        latest_data = df.tail(10)  # 最近10个交易日
        current_price = float(df['收盘'].iloc[-1])
        
        # 计算KDAS相关数据
        kdas_info = {}
        support_levels = []  # 支撑位
        resistance_levels = []  # 压力位
        
        for key, date_str in input_dates.items():
            kdas_col = f'KDAS{date_str}'
            if kdas_col in df.columns:
                kdas_series = df[kdas_col].dropna()
                if not kdas_series.empty:
                    latest_kdas = float(kdas_series.iloc[-1])
                    kdas_info[key] = {
                        'value': latest_kdas,
                        'start_date': datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d'),
                        'trend': 'up' if len(kdas_series) > 5 and kdas_series.iloc[-1] > kdas_series.iloc[-6] else 'down'
                    }
                    
                    # 分类支撑位和压力位
                    if latest_kdas < current_price:
                        support_levels.append(latest_kdas)
                    elif latest_kdas > current_price:
                        resistance_levels.append(latest_kdas)
        
        # 支撑位和压力位排序
        support_levels.sort(reverse=True)  # 支撑位从高到低
        resistance_levels.sort()  # 压力位从低到高
        
        # 成交量分析
        recent_volume = latest_data['成交量'].mean()
        volume_trend = 'increasing' if latest_data['成交量'].iloc[-1] > recent_volume else 'decreasing'
        
        # 价格波动分析
        price_volatility = float(latest_data['收盘'].std())
        price_trend = 'up' if latest_data['收盘'].iloc[-1] > latest_data['收盘'].iloc[0] else 'down'
        
        # KDAS均线发散/收敛分析
        kdas_values = [info['value'] for info in kdas_info.values()]
        kdas_dispersion = float(np.std(kdas_values)) if len(kdas_values) > 1 else 0
        
        return {
            'security_info': {
                'name': security_name,
                'symbol': symbol,
                'type': security_type,
                'current_price': current_price,
                'data_period': f"{df['日期'].iloc[0].strftime('%Y-%m-%d')} 至 {df['日期'].iloc[-1].strftime('%Y-%m-%d')}"
            },
            'kdas_info': kdas_info,
            'support_levels': support_levels[:3],  # 最近3个支撑位
            'resistance_levels': resistance_levels[:3],  # 最近3个压力位
            'market_data': {
                'recent_volume_avg': float(recent_volume),
                'volume_trend': volume_trend,
                'price_volatility': price_volatility,
                'price_trend': price_trend,
                'latest_volume': float(latest_data['成交量'].iloc[-1]),
                'latest_high': float(latest_data['最高'].iloc[-1]),
                'latest_low': float(latest_data['最低'].iloc[-1])
            },
            'kdas_system': {
                'dispersion': kdas_dispersion,
                'convergence_status': 'converging' if kdas_dispersion < current_price * 0.01 else 'diverging',
                'num_above_price': len([k for k in kdas_values if k > current_price]),
                'num_below_price': len([k for k in kdas_values if k < current_price])
            }
        }

    def _prepare_kdas_analysis_prompt(self, analysis_data: Dict) -> str:
        """准备KDAS状态分析的prompt"""
        
        security_info = analysis_data.get('security_info', {})
        kdas_info = analysis_data.get('kdas_info', {})
        support_levels = analysis_data.get('support_levels', [])
        resistance_levels = analysis_data.get('resistance_levels', [])
        market_data = analysis_data.get('market_data', {})
        kdas_system = analysis_data.get('kdas_system', {})
        
        prompt = f"""
你是一位精通KDAS交易体系的专业技术分析师，请基于以下数据对当前市场状态进行深度分析。

KDAS交易体系理论框架：

核心内容：四种状态的KDAS
关键词：多空力量平衡、趋势确认、情绪宣泄、市场一致性

支持判断、协助制定策略"关键位"，只采用趋势单：
- 从下方升到KDAS均线以上时，只做多KDAS分时强点
- 从上方跌到KDAS均线下方时，只做空KDAS分时强点

一、趋势行进状态
1. 趋势确认：当前价格在KDAS线上方（多）或下方（空），且均线发散，方向一致
2. 高位/低位蓄能：价格仍在KDAS均线上方，但均线开始收拢，价格横盘震荡

二、趋势衰竭状态  
1. 情绪宣泄：价格脱离KDAS线出现极端运行，多空力量临时失衡
2. 趋势反转：出现明显背离/结构破坏，KDAS均线系统掉头

三、趋势衰竭后的震荡状态
1. 多空力量一致：市场整体节奏一致，无明显分歧
2. 多空分歧剧烈：市场内部观点分歧剧烈，多空反复试探

四、整理状态
1. 情绪积累：无量波动、价格震荡，市场预期累积
2. 整体盘整：KDAS系统失去方向性，价格围绕中轴反复运行

当前证券分析数据：

证券基本信息：
- 名称：{security_info.get('name', '未知')}
- 代码：{security_info.get('symbol', '未知')}
- 类型：{security_info.get('type', '未知')}
- 当前价格：¥{security_info.get('current_price', 0):.3f}
- 数据周期：{security_info.get('data_period', '未知')}

KDAS系统状态：
"""
        
        # 添加KDAS详细信息
        for key, info in kdas_info.items():
            prompt += f"- {key}: ¥{info['value']:.3f} (起始日期: {info['start_date']}, 趋势: {info['trend']})\n"
        
        prompt += f"""
支撑压力位分析：
- 主要支撑位：{[f'¥{level:.3f}' for level in support_levels]}
- 主要压力位：{[f'¥{level:.3f}' for level in resistance_levels]}

市场数据：
- 最新成交量：{market_data.get('latest_volume', 0):,.0f}
- 近期平均成交量：{market_data.get('recent_volume_avg', 0):,.0f}
- 成交量趋势：{market_data.get('volume_trend', '未知')}
- 价格波动率：{market_data.get('price_volatility', 0):.3f}
- 价格趋势：{market_data.get('price_trend', '未知')}

KDAS系统特征：
- 均线发散度：{kdas_system.get('dispersion', 0):.3f}
- 收敛状态：{kdas_system.get('convergence_status', '未知')}
- 价格上方KDAS数量：{kdas_system.get('num_above_price', 0)}
- 价格下方KDAS数量：{kdas_system.get('num_below_price', 0)}

请基于KDAS交易体系理论，深度分析当前市场状态，用专业但易懂的语言进行分析，帮助投资者更好地理解当前市场状态，以JSON格式返回你的结果：
```json
{{
    "状态": "当前KD判断当前属于上述四种状态中的哪一种，并详细说明判断依据AS状态",
    "多空力量分析": "分析当前多空力量对比，以及价格与KDAS系统的位置关系",
    "趋势方向判断": "基于KDAS系统判断当前趋势方向和强度",
    "交易建议": "根据KDAS体系给出具体的交易策略建议",
    "风险提示": "基于当前状态的风险评估和注意事项",
    "置信度": "以上分析的回答置信度，从高到低分为：高、中、低"
}}
```
"""
        
        return prompt

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
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
            self.async_client = AsyncOpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
        else:
            return {
                'success': False,
                'error': 'AI API密钥未配置',
                'recommendation': None,
                'analysis': None
            }
        
        try:
            # 1. 获取证券信息
            security_name = self._get_security_name(symbol, security_type)
            
            # 2. 获取证券数据 - 使用默认的时间范围
            default_dates = self._generate_default_dates()
            df = self._get_security_data_internal(symbol, default_dates, security_type)
            
            if df.empty:
                return {
                    'success': False,
                    'error': f'未找到该{security_type}的数据，请检查{security_type}代码是否正确',
                    'recommendation': None,
                    'analysis': None
                }
            
            # 3. 先进行日期推荐
            recommendation_result = await self.generate_kdas_recommendation_async(
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
            input_dates = {}
            for i, date_str in enumerate(recommended_dates[:5], 1):
                # 将YYYY-MM-DD格式转换为YYYYMMDD格式
                formatted_date = date_str.replace('-', '')
                input_dates[f'day{i}'] = formatted_date
            
            # 重新获取数据以确保包含推荐日期的范围
            df_with_kdas = self._get_security_data_internal(symbol, input_dates, security_type)
            
            if df_with_kdas.empty:
                return {
                    'success': False,
                    'error': '重新获取数据失败',
                    'recommendation': recommendation_result,
                    'analysis': None
                }
            
            # 5. 计算KDAS
            df_processed = self._calculate_cumulative_vwap(df_with_kdas, input_dates)
            
            # 6. 进行KDAS状态分析
            analysis_result = await self.analyze_kdas_state_async(
                df_processed, input_dates, symbol, security_name, security_type
            )
            
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
                'data_summary': {
                    'total_records': len(df_processed),
                    'date_range': f"{df_processed['日期'].iloc[0].strftime('%Y-%m-%d')} 至 {df_processed['日期'].iloc[-1].strftime('%Y-%m-%d')}",
                    'current_price': float(df_processed['收盘'].iloc[-1])
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'完整分析失败: {str(e)}',
                'recommendation': None,
                'analysis': None
            }
    
    def _get_security_name(self, symbol: str, security_type: str) -> str:
        """获取证券名称"""
        try:
            import akshare as ak
            
            # 清理代码格式
            symbol = symbol.split('.')[0]
            
            if security_type == "股票":
                # 尝试从本地文件获取
                if os.path.exists('shares/A股全部股票代码.csv'):
                    stock_info_df = pd.read_csv('shares/A股全部股票代码.csv', dtype={0: str})
                    if '股票代码' in stock_info_df.columns and '股票名称' in stock_info_df.columns:
                        stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
                else:
                    stock_info_df = ak.stock_info_a_code_name()
                    stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
                
                name_series = stock_info_df[stock_info_df["code"] == symbol]["name"]
                return name_series.values[0] if len(name_series) > 0 else f"未知股票"
                
            elif security_type == "ETF":
                # 尝试从本地文件获取
                if os.path.exists('etfs/A股全部ETF代码.csv'):
                    etf_info_df = pd.read_csv('etfs/A股全部ETF代码.csv', dtype={0: str})
                else:
                    etf_info_df = ak.fund_etf_spot_em()
                    etf_info_df = etf_info_df[['代码', '名称']].drop_duplicates().rename(columns={"代码": "code", "名称": "name"})
                
                name_series = etf_info_df[etf_info_df["code"] == symbol]["name"]
                return name_series.values[0] if len(name_series) > 0 else f"未知ETF"
                
            else:
                return f"未知{security_type}"
                
        except Exception as e:
            return f"未知{security_type}"
    
    def _generate_default_dates(self) -> Dict:
        """生成默认的日期范围用于数据获取"""
        # 生成一个较大的时间范围以确保能获取足够的历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 一年的数据
        
        return {
            'day1': start_date.strftime('%Y%m%d'),
            'day2': (start_date + timedelta(days=90)).strftime('%Y%m%d'),
            'day3': (start_date + timedelta(days=180)).strftime('%Y%m%d'),
            'day4': (start_date + timedelta(days=270)).strftime('%Y%m%d'),
            'day5': end_date.strftime('%Y%m%d')
        }
    
    def _get_security_data_internal(self, symbol: str, input_date: Dict, security_type: str = "股票") -> pd.DataFrame:
        """内部数据获取函数，复用KDAS.py中的逻辑"""
        try:
            import akshare as ak
            
            # 转换代码格式（如300328.SZ -> 300328）
            symbol = symbol.split('.')[0]
            start_date = min(input_date.values())
            today = datetime.now().strftime('%Y%m%d')
            
            # 根据证券类型选择文件夹和API
            if security_type == "股票":
                folder = 'shares'
                api_func = lambda: ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, adjust="qfq")
                api_func_update = lambda last_date: ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=last_date, adjust="qfq")
            elif security_type == "ETF":
                folder = 'etfs'
                api_func = lambda: ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date, adjust="qfq")
                api_func_update = lambda last_date: ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=last_date, adjust="qfq")
            elif security_type == "指数":
                folder = 'stocks'
                api_func = lambda: ak.stock_zh_index_daily(symbol=symbol, start_date=start_date)
                api_func_update = lambda last_date: ak.stock_zh_index_daily(symbol=symbol, start_date=last_date)
            else:
                raise ValueError(f"不支持的证券类型: {security_type}")
            
            # 确保文件夹存在
            os.makedirs(folder, exist_ok=True)
            file_path = f'{folder}/{symbol}.csv'
            
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['日期'] = pd.to_datetime(df['日期'])
                
                # 转换start_date为Timestamp以便比较
                start_date_ts = pd.to_datetime(start_date)
                if not (df['日期'] == start_date_ts).any():
                    df = api_func()
                    if not df.empty:
                        # 确保日期列格式正确
                        df['日期'] = pd.to_datetime(df['日期'])
                        df.to_csv(file_path, index=False)
                else:
                    # 检查是否需要更新数据
                    last_date_in_df = df['日期'].iloc[-1]
                    today_ts = pd.to_datetime(today)
                    if last_date_in_df < today_ts:
                        df_add = api_func_update(last_date_in_df.strftime('%Y%m%d'))
                        if not df_add.empty:
                            # 确保新数据的日期列格式正确
                            df_add['日期'] = pd.to_datetime(df_add['日期'])
                            df.drop(index=df.index[-1], inplace=True)
                            df = pd.concat([df, df_add], ignore_index=True)
                            # 去重并排序
                            df = df.drop_duplicates(subset=['日期']).sort_values('日期').reset_index(drop=True)
                            df.to_csv(file_path, index=False)
            else:
                df = api_func()
                if not df.empty:
                    # 确保日期列格式正确
                    df['日期'] = pd.to_datetime(df['日期'])
                    df.to_csv(file_path, index=False)
            
            # 确保数据不为空且格式正确
            if df.empty:
                return df
                
            # 基本数据清理 - 确保日期列是Timestamp格式
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期').reset_index(drop=True)
            
            # 标准化列名，确保一致性
            if security_type == "指数" and '股票代码' not in df.columns:
                # 指数数据可能没有股票代码列，需要添加
                df['股票代码'] = symbol
            
            return df
            
        except Exception as e:
            raise Exception(f"获取证券数据失败: {str(e)}")
    
    def _calculate_cumulative_vwap(self, df: pd.DataFrame, input_date: Dict) -> pd.DataFrame:
        """计算KDAS，复用KDAS.py中的逻辑"""
        df = df.copy()
        df['日期'] = pd.to_datetime(df['日期'])
        
        for key, value in input_date.items():
            target_date = datetime.strptime(value, "%Y%m%d").date()
            start_idx = df[df['日期'].dt.date == target_date].index
            if len(start_idx) > 0:
                start_idx = start_idx[0]
                # 初始化列为NaN
                df[f'累计成交额{value}'] = pd.Series(dtype=float)
                df[f'累计成交量{value}'] = pd.Series(dtype=float)
                df[f'KDAS{value}'] = pd.Series(dtype=float)
                
                # 只对从start_idx开始的行进行累计计算
                df.loc[start_idx:, f'累计成交额{value}'] = df.loc[start_idx:, '成交额'].cumsum()
                df.loc[start_idx:, f'累计成交量{value}'] = df.loc[start_idx:, '成交量'].cumsum()
                df.loc[start_idx:, f'KDAS{value}'] = (df.loc[start_idx:, f'累计成交额{value}'] / df.loc[start_idx:, f'累计成交量{value}'] / 100).round(3)
        
        return df

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