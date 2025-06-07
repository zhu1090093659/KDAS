from openai import OpenAI, AsyncOpenAI
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import re
from typing import List, Dict, Optional
from .technical_analysis import TechnicalAnalyzer


class AIRecommendationEngine:
    """AI推荐引擎 - 负责基于技术分析生成KDAS日期推荐"""
    
    def __init__(self, api_key: str = None, model: str = "deepseek-r1"):
        """
        初始化AI推荐引擎
        
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
        
        self.technical_analyzer = TechnicalAnalyzer()
    
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
            technical_analysis = self.technical_analyzer.analyze_technical_indicators(df)
            
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
            technical_analysis = self.technical_analyzer.analyze_technical_indicators(df)
            
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
4. 最后日期必须在当前日期十个交易日以内，今天日期为{datetime.now().strftime('%Y-%m-%d')}

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