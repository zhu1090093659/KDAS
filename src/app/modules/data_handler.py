"""
数据处理模块 - KDAS证券分析工具

负责处理所有数据相关的操作，包括：
- 证券信息加载（股票、ETF、指数）
- 证券数据获取和缓存
- KDAS指标计算
- 交易日历处理
- 数据验证和清理

作者：KDAS团队
版本：2.0 (模块化重构版本)
"""

import os
import pandas as pd
import streamlit as st
import akshare as ak
from datetime import datetime, timedelta

# === KDAS包导入与初始化 ===
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from kdas import DataHandler
    KDAS_HANDLER_AVAILABLE = True
    # 初始化全局数据处理器
    data_handler = DataHandler()
except ImportError:
    KDAS_HANDLER_AVAILABLE = False
    data_handler = None

class DataManager:
    """数据管理器类，封装所有数据处理功能"""
    
    def __init__(self):
        """初始化数据管理器"""
        # 数据目录路径（相对于项目根目录）
        self.data_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
        self._ensure_data_directories()
        
        # 初始化kdas数据处理器
        self.kdas_handler = data_handler
    
    def _ensure_data_directories(self):
        """确保数据目录存在"""
        os.makedirs(os.path.join(self.data_root, 'shares'), exist_ok=True)
        os.makedirs(os.path.join(self.data_root, 'etfs'), exist_ok=True)
        os.makedirs(os.path.join(self.data_root, 'stocks'), exist_ok=True)
    
    @st.cache_data
    def load_stock_info(_self):
        """缓存加载股票信息"""
        if _self.kdas_handler is None:
            # 备用方案：直接使用akshare
            stock_file_path_backup = os.path.join(_self.data_root, 'shares', 'A股全部股票代码.csv')
            if os.path.exists(stock_file_path_backup):
                stock_info_df = pd.read_csv(stock_file_path_backup, dtype={0: str})
                if '股票代码' in stock_info_df.columns and '股票名称' in stock_info_df.columns:
                    stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
            else:
                stock_info_df = ak.stock_info_a_code_name()
                stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
                stock_info_df.to_csv(stock_file_path_backup, index=False)
            return stock_info_df
        
        # 使用kdas.DataHandler的逻辑
        stock_file_path = os.path.join(_self.data_root, 'shares', 'A股全部股票代码.csv')
        if os.path.exists(stock_file_path):
            stock_info_df = pd.read_csv(stock_file_path, dtype={0: str})
            if '股票代码' in stock_info_df.columns and '股票名称' in stock_info_df.columns:
                stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
        else:
            stock_info_df = ak.stock_info_a_code_name()
            stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
            stock_info_df.to_csv(stock_file_path, index=False)
        return stock_info_df
    
    @st.cache_data
    def load_etf_info(_self):
        """缓存加载ETF信息"""
        etf_file_path = os.path.join(_self.data_root, 'etfs', 'A股全部ETF代码.csv')
        if os.path.exists(etf_file_path):
            etf_info_df = pd.read_csv(etf_file_path, dtype={0: str})
        else:
            etf_info_df = ak.fund_etf_spot_em()  # 东财A股全部ETF
            etf_info_df = etf_info_df[['代码', '名称']].drop_duplicates().rename(columns={"代码": "code", "名称": "name"})
            etf_info_df.to_csv(etf_file_path, index=False)
        return etf_info_df
    
    @st.cache_data
    def load_index_info(_self):
        """缓存加载指数信息"""
        index_file_path = os.path.join(_self.data_root, 'stocks', 'A股全部指数代码.csv')
        if os.path.exists(index_file_path):
            index_info_df = pd.read_csv(index_file_path, dtype={0: str})
        else:
            categories = ("沪深重要指数", "上证系列指数", "深证系列指数", "指数成份", "中证系列指数")
            index_dfs = []
            for category in categories:
                df = ak.stock_zh_index_spot_em(symbol=category)
                index_dfs.append(df)
            # 合并数据并去重
            index_info_df = pd.concat(index_dfs).drop_duplicates(subset=["代码"])
            index_info_df = index_info_df[["代码", "名称"]].rename(columns={"代码": "code", "名称": "name"})
            index_info_df.to_csv(index_file_path, index=False)
        return index_info_df
    
    @st.cache_data
    def get_security_data(_self, symbol, input_date, security_type="股票"):
        """获取证券数据，使用kdas.DataHandler或备用方案"""
        if _self.kdas_handler is None:
            # 备用方案：使用原始实现
            try:
                symbol = symbol.split('.')[0]
                start_date = min(input_date.values())
                today = datetime.now().strftime('%Y%m%d')
                
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
                
                file_path = os.path.join(_self.data_root, folder, f'{symbol}.csv')
                
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    df['日期'] = pd.to_datetime(df['日期'])
                    
                    start_date_ts = pd.to_datetime(start_date)
                    if not (df['日期'] == start_date_ts).any():
                        df = api_func()
                        if not df.empty:
                            df['日期'] = pd.to_datetime(df['日期'])
                            df.to_csv(file_path, index=False)
                    else:
                        last_date_in_df = df['日期'].iloc[-1]
                        today_ts = pd.to_datetime(today)
                        if last_date_in_df < today_ts:
                            df_add = api_func_update(last_date_in_df.strftime('%Y%m%d'))
                            if not df_add.empty:
                                df_add['日期'] = pd.to_datetime(df_add['日期'])
                                df.drop(index=df.index[-1], inplace=True)
                                df = pd.concat([df, df_add], ignore_index=True)
                                df = df.drop_duplicates(subset=['日期']).sort_values('日期').reset_index(drop=True)
                                df.to_csv(file_path, index=False)
                else:
                    df = api_func()
                    if not df.empty:
                        df['日期'] = pd.to_datetime(df['日期'])
                        df.to_csv(file_path, index=False)
                
                if df.empty:
                    return df
                    
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.sort_values('日期').reset_index(drop=True)
                
                if security_type == "指数" and '股票代码' not in df.columns:
                    df['股票代码'] = symbol
                
                return df
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                raise Exception(f"get_security_data函数执行失败: {str(e)}\n详细错误:\n{error_details}")
        
        # 使用kdas.DataHandler
        try:
            return _self.kdas_handler.get_security_data(symbol, input_date, security_type)
        except Exception as e:
            raise Exception(f"kdas.DataHandler获取数据失败: {str(e)}")
    
    def calculate_cumulative_vwap(self, df, input_date):
        """
        计算KDAS指标，使用kdas.DataHandler或备用方案
        
        Args:
            df: 证券数据DataFrame
            input_date: 输入日期字典，格式为 {'day1': 'YYYYMMDD', ...}
            
        Returns:
            包含KDAS计算结果的DataFrame
        """
        if self.kdas_handler is None:
            # 备用方案：使用原始实现
            df = df.copy()  # 避免修改原始数据
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
        
        # 使用kdas.DataHandler - 高效且经过优化的实现
        try:
            return self.kdas_handler.calculate_cumulative_vwap(df, input_date)
        except Exception as e:
            # 如果kdas包出现问题，回退到备用方案
            st.warning(f"kdas包计算KDAS时出现问题，使用备用方案: {str(e)}")
            df = df.copy()
            df['日期'] = pd.to_datetime(df['日期'])
            for key, value in input_date.items():
                target_date = datetime.strptime(value, "%Y%m%d").date()
                start_idx = df[df['日期'].dt.date == target_date].index
                if len(start_idx) > 0:
                    start_idx = start_idx[0]
                    df[f'累计成交额{value}'] = pd.Series(dtype=float)
                    df[f'累计成交量{value}'] = pd.Series(dtype=float)
                    df[f'KDAS{value}'] = pd.Series(dtype=float)
                    
                    df.loc[start_idx:, f'累计成交额{value}'] = df.loc[start_idx:, '成交额'].cumsum()
                    df.loc[start_idx:, f'累计成交量{value}'] = df.loc[start_idx:, '成交量'].cumsum()
                    df.loc[start_idx:, f'KDAS{value}'] = (df.loc[start_idx:, f'累计成交额{value}'] / df.loc[start_idx:, f'累计成交量{value}'] / 100).round(3)
            return df
    
    def get_security_name(self, symbol, security_type):
        """获取证券名称"""
        if self.kdas_handler is None:
            # 备用方案：查找对应的info_df
            if security_type == "股票":
                info_df = self.load_stock_info()
            elif security_type == "ETF":
                info_df = self.load_etf_info()
            elif security_type == "指数":
                info_df = self.load_index_info()
            else:
                return f"未知{security_type}"
            
            symbol = str(symbol).split('.')[0]
            security_name = info_df[info_df["code"] == symbol]["name"].values
            return security_name[0] if len(security_name) > 0 else f"未知{security_type}"
        
        # 使用kdas.DataHandler
        return self.kdas_handler.get_security_name(symbol, security_type)
    
    @st.cache_data
    def get_trade_calendar(_self):
        """获取中国股市官方交易日历数据"""
        try:
            # 使用akshare获取交易日历
            trade_calendar_df = ak.tool_trade_date_hist_sina()
            # 转换为日期格式
            trade_calendar_df['trade_date'] = pd.to_datetime(trade_calendar_df['trade_date'])
            return trade_calendar_df['trade_date'].dt.date.tolist()
        except Exception as e:
            print(f"获取交易日历失败: {e}")
            # 如果获取失败，返回空列表，后续会使用备用方案
            return []
    
    def get_non_trading_dates(self, start_date, end_date):
        """获取指定日期范围内的非交易日"""
        trade_dates = self.get_trade_calendar()
        
        if not trade_dates:
            # 如果获取交易日历失败，使用备用方案（基本节假日）
            return self.get_basic_holidays()
        
        # 转换日期范围
        start_dt = pd.to_datetime(start_date).date() if isinstance(start_date, str) else start_date
        end_dt = pd.to_datetime(end_date).date() if isinstance(end_date, str) else end_date
        
        # 获取所有日期
        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        trade_dates_set = set(trade_dates)
        
        # 找出非交易日（排除周末，因为rangebreaks会单独处理周末）
        non_trading_dates = []
        for date in all_dates:
            if date.weekday() < 5:  # 只考虑工作日
                if date.date() not in trade_dates_set:
                    non_trading_dates.append(date.strftime('%Y-%m-%d'))
        
        return non_trading_dates
    
    def get_basic_holidays(self):
        """备用方案：基本节假日列表（当无法获取官方交易日历时使用）"""
        return [
            # 只保留主要节假日作为备用
            "2024-01-01", "2024-02-10", "2024-02-11", "2024-02-12", "2024-02-13", 
            "2024-02-14", "2024-02-15", "2024-02-16", "2024-02-17", "2024-04-04", 
            "2024-04-05", "2024-04-06", "2024-05-01", "2024-05-02", "2024-05-03", 
            "2024-06-10", "2024-09-15", "2024-09-16", "2024-09-17", "2024-10-01", 
            "2024-10-02", "2024-10-03", "2024-10-04", "2024-10-07",
            "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
            "2025-02-01", "2025-02-02", "2025-02-03", "2025-02-04", "2025-04-05", 
            "2025-04-06", "2025-04-07", "2025-05-01", "2025-05-02", "2025-05-03", 
            "2025-05-31", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-06", 
            "2025-10-07", "2025-10-08"
        ]

# === 全局数据管理器实例 ===
data_manager = DataManager()

# === 向后兼容的全局函数接口 ===
def load_stock_info():
    """加载股票信息 - 向后兼容接口"""
    return data_manager.load_stock_info()

def load_etf_info():
    """加载ETF信息 - 向后兼容接口"""
    return data_manager.load_etf_info()

def load_index_info():
    """加载指数信息 - 向后兼容接口"""
    return data_manager.load_index_info()

def get_security_data(symbol, input_date, security_type="股票"):
    """获取证券数据 - 向后兼容接口"""
    return data_manager.get_security_data(symbol, input_date, security_type)

def calculate_cumulative_vwap(df, input_date):
    """计算KDAS指标 - 向后兼容接口"""
    return data_manager.calculate_cumulative_vwap(df, input_date)

def get_security_name(symbol, security_type):
    """获取证券名称 - 向后兼容接口"""
    return data_manager.get_security_name(symbol, security_type)

def get_trade_calendar():
    """获取交易日历 - 向后兼容接口"""
    return data_manager.get_trade_calendar()

def get_non_trading_dates(start_date, end_date):
    """获取非交易日 - 向后兼容接口"""
    return data_manager.get_non_trading_dates(start_date, end_date)

def get_basic_holidays():
    """获取基本节假日 - 向后兼容接口"""
    return data_manager.get_basic_holidays()

# === 数据目录路径常量 ===
data_root = data_manager.data_root 