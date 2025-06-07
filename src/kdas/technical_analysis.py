import pandas as pd
import numpy as np
from typing import List, Dict
from .utils import safe_json_convert


class TechnicalAnalyzer:
    """技术分析器类 - 负责计算各种技术指标"""
    
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