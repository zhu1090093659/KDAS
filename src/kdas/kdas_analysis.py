from openai import OpenAI, AsyncOpenAI
import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import Dict


class KDASAnalyzer:
    """KDAS分析器 - 负责分析KDAS交易状态"""
    
    def __init__(self, api_key: str = None, model: str = "deepseek-r1"):
        """
        初始化KDAS分析器
        
        Args:
            api_key: AI API密钥
            model: 要使用的AI模型名称
        """
        self.api_key = api_key
        self.model = model
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
            self.async_client = AsyncOpenAI(api_key=self.api_key, base_url="https://chatwithai.icu/v1")
        else:
            self.client = None
            self.async_client = None

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
                        "content": f"你是一位专业的股票技术分析师，精通KDAS交易体系。当前使用的AI模型是{self.model}。请基于KDAS数据给出专业的状态分析，确保回复格式严格按照JSON格式。"
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
            raise Exception(f"KDAS分析GPT调用失败: {str(e)}")
    
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
                        "content": f"你是一位专业的股票技术分析师，精通KDAS交易体系。当前使用的AI模型是{self.model}。请基于KDAS数据给出专业的状态分析，确保回复格式严格按照JSON格式。"
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
            raise Exception(f"异步KDAS分析GPT调用失败: {str(e)}") 