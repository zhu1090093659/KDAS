import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Dict, List
import asyncio


class DataHandler:
    """数据处理器 - 负责证券数据获取、处理和KDAS计算"""
    
    def __init__(self):
        """初始化数据处理器"""
        pass
    
    def get_security_name(self, symbol: str, security_type: str) -> str:
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
    
    def generate_default_dates(self) -> Dict:
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
    
    def get_security_data(self, symbol: str, input_date: Dict, security_type: str = "股票") -> pd.DataFrame:
        """获取证券数据"""
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
    
    def calculate_cumulative_vwap(self, df: pd.DataFrame, input_date: Dict) -> pd.DataFrame:
        """计算KDAS（累计成交量加权平均价格）"""
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

    async def batch_get_securities_data(self, securities_list: List[Dict]) -> List[Dict]:
        """
        批量异步获取多个证券的数据
        
        Args:
            securities_list: 证券列表，每个元素包含：
                - security_type: str ("股票" 或 "ETF")
                - symbol: str (证券代码)
                
        Returns:
            包含所有证券数据的列表
        """
        try:
            # 为每个证券创建数据获取任务
            tasks = []
            for security_info in securities_list:
                # 为每个证券生成默认日期
                default_dates = self.generate_default_dates()
                
                # 创建数据获取任务（包装为协程）
                task = self._get_single_security_data_async(
                    symbol=security_info['symbol'],
                    security_type=security_info['security_type'],
                    input_dates=default_dates
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
                        'error': f'证券{symbol}数据获取失败: {str(result)}',
                        'symbol': symbol,
                        'data': None
                    })
                else:
                    final_results.append({
                        'success': True,
                        'symbol': symbol,
                        'data': result
                    })
            
            return final_results
            
        except Exception as e:
            return [{
                'success': False,
                'error': f'批量数据获取失败: {str(e)}',
                'symbol': security.get('symbol', '未知'),
                'data': None
            } for security in securities_list]

    async def _get_single_security_data_async(self, symbol: str, security_type: str, input_dates: Dict) -> pd.DataFrame:
        """
        异步获取单个证券数据的包装函数
        
        Args:
            symbol: 证券代码
            security_type: 证券类型
            input_dates: 输入日期字典
            
        Returns:
            证券数据DataFrame
        """
        # 将同步的数据获取函数在线程池中执行，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.get_security_data, 
            symbol, 
            input_dates, 
            security_type
        )

    def format_dates_for_kdas(self, date_list: List[str]) -> Dict:
        """
        将日期列表转换为KDAS计算所需的格式
        
        Args:
            date_list: 日期字符串列表，格式为['YYYY-MM-DD', ...]
            
        Returns:
            格式化后的日期字典，格式为{'day1': 'YYYYMMDD', ...}
        """
        input_dates = {}
        for i, date_str in enumerate(date_list[:5], 1):  # 最多取5个日期
            # 将YYYY-MM-DD格式转换为YYYYMMDD格式
            formatted_date = date_str.replace('-', '')
            input_dates[f'day{i}'] = formatted_date
        
        return input_dates

    def get_data_summary(self, df: pd.DataFrame) -> Dict:
        """
        获取数据摘要信息
        
        Args:
            df: 数据DataFrame
            
        Returns:
            数据摘要字典
        """
        if df.empty:
            return {
                'total_records': 0,
                'date_range': '无数据',
                'current_price': 0.0
            }
        
        return {
            'total_records': len(df),
            'date_range': f"{df['日期'].iloc[0].strftime('%Y-%m-%d')} 至 {df['日期'].iloc[-1].strftime('%Y-%m-%d')}",
            'current_price': float(df['收盘'].iloc[-1])
        }

    def validate_input_dates(self, input_dates: Dict, df: pd.DataFrame) -> Dict:
        """
        验证输入日期是否在数据范围内
        
        Args:
            input_dates: 输入日期字典
            df: 数据DataFrame
            
        Returns:
            验证结果字典
        """
        if df.empty:
            return {
                'valid': False,
                'error': '数据为空',
                'validated_dates': {}
            }
        
        validated_dates = {}
        df_dates = df['日期'].dt.strftime('%Y%m%d').tolist()
        
        for key, date_str in input_dates.items():
            if date_str in df_dates:
                validated_dates[key] = date_str
            else:
                # 寻找最接近的日期
                target_date = datetime.strptime(date_str, '%Y%m%d')
                available_dates = [datetime.strptime(d, '%Y%m%d') for d in df_dates]
                closest_date = min(available_dates, key=lambda x: abs((x - target_date).days))
                validated_dates[key] = closest_date.strftime('%Y%m%d')
        
        return {
            'valid': True,
            'validated_dates': validated_dates,
            'original_dates': input_dates
        } 