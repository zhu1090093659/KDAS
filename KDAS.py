import os
import akshare as ak
import pandas as pd
from datetime import datetime, date
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import json

os.makedirs('shares', exist_ok=True)
os.makedirs('etfs', exist_ok=True)
os.makedirs('stocks', exist_ok=True)

# 配置文件路径
CONFIG_FILE = 'user_configs.json'

def load_user_configs():
    """加载用户保存的配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    return {}

def save_user_configs(configs):
    """保存用户配置"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(configs, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False

def save_current_config(symbol, security_type, input_date, security_name):
    """保存当前的配置"""
    configs = load_user_configs()
    config_key = f"{security_type}_{symbol}"
    
    configs[config_key] = {
        'symbol': symbol,
        'security_type': security_type,
        'security_name': security_name,
        'dates': input_date,
        'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return save_user_configs(configs)

def get_saved_config(symbol, security_type):
    """获取指定证券的保存配置"""
    configs = load_user_configs()
    config_key = f"{security_type}_{symbol}"
    return configs.get(config_key, None)

def delete_saved_config(symbol, security_type):
    """删除指定证券的保存配置"""
    configs = load_user_configs()
    config_key = f"{security_type}_{symbol}"
    if config_key in configs:
        del configs[config_key]
        return save_user_configs(configs)
    return False

@st.cache_data
def load_stock_info():
    """缓存加载股票信息"""
    if os.path.exists('shares/A股全部股票代码.csv'):
        stock_info_df = pd.read_csv('shares/A股全部股票代码.csv', dtype={0: str})
        # 确保列名正确
        if '股票代码' in stock_info_df.columns and '股票名称' in stock_info_df.columns:
            stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
    else:
        stock_info_df = ak.stock_info_a_code_name()
        # 标准化列名
        stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
        stock_info_df.to_csv('shares/A股全部股票代码.csv', index=False)
    return stock_info_df

@st.cache_data
def load_etf_info():
    """缓存加载ETF信息"""
    if os.path.exists('etfs/A股全部ETF代码.csv'):
        etf_info_df = pd.read_csv('etfs/A股全部ETF代码.csv', dtype={0: str})
    else:
        etf_info_df = ak.fund_etf_spot_em()  # 东财A股全部ETF
        etf_info_df = etf_info_df[['代码', '名称']].drop_duplicates().rename(columns={"代码": "code", "名称": "name"})
        etf_info_df.to_csv('etfs/A股全部ETF代码.csv', index=False)
    return etf_info_df

@st.cache_data
def load_index_info():
    """缓存加载指数信息"""
    if os.path.exists('stocks/A股全部指数代码.csv'):
        index_info_df = pd.read_csv('stocks/A股全部指数代码.csv', dtype={0: str})
    else:
        categories = ("沪深重要指数", "上证系列指数", "深证系列指数", "指数成份", "中证系列指数")
        index_dfs = []
        for category in categories:
            df = ak.stock_zh_index_spot_em(symbol=category)
            index_dfs.append(df)
        # 合并数据并去重
        index_info_df = pd.concat(index_dfs).drop_duplicates(subset=["代码"])
        index_info_df = index_info_df[["代码", "名称"]].rename(columns={"代码": "code", "名称": "name"})
        index_info_df.to_csv('stocks/A股全部指数代码.csv', index=False)
    return index_info_df

# 获取历史数据（股票、ETF、指数）
@st.cache_data
def get_security_data(symbol, input_date, security_type="股票"):
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
    
    file_path = f'{folder}/{symbol}.csv'
    
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['日期'] = pd.to_datetime(df['日期'])
        
        if not pd.to_datetime(start_date) in df['日期'].values:
            df = api_func()
            if not df.empty:
                df.to_csv(file_path, index=False)
        elif df['日期'].iloc[-1] < pd.to_datetime(datetime.now().date()):
            df_add = api_func_update(df['日期'].iloc[-1].strftime('%Y%m%d'))
            if not df_add.empty:
                df.drop(index=df.index[-1], inplace=True)
                df = pd.concat([df, df_add], ignore_index=True)
                # 去重并排序
                df = df.drop_duplicates(subset=['日期']).sort_values('日期').reset_index(drop=True)
                df.to_csv(file_path, index=False)
    else:
        df = api_func()
        if not df.empty:
            df.to_csv(file_path, index=False)
    
    # 确保数据不为空且格式正确
    if df.empty:
        return df
        
    # 基本数据清理
    df['日期'] = pd.to_datetime(df['日期'])
    df = df.sort_values('日期').reset_index(drop=True)
    
    # 标准化列名，确保一致性
    if security_type == "指数" and '股票代码' not in df.columns:
        # 指数数据可能没有股票代码列，需要添加
        df['股票代码'] = symbol
    
    return df

@st.cache_data
def get_trade_calendar():
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

def get_non_trading_dates(start_date, end_date):
    """获取指定日期范围内的非交易日"""
    trade_dates = get_trade_calendar()
    
    if not trade_dates:
        # 如果获取交易日历失败，使用备用方案（基本节假日）
        return get_basic_holidays()
    
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

def get_basic_holidays():
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

# KDAS计算
def calculate_cumulative_vwap(df, input_date):
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

def create_interactive_chart(df, input_date, info_df, security_type="股票", symbol_code=None):
    """创建交互式图表"""
    # 创建子图：上方K线图+KDAS，下方成交量
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=('K线图与KDAS指标', '成交量'),
        row_heights=[0.75, 0.25]  # 上图占75%，下图占25%
    )
    
    # 确保数据按日期排序并过滤掉无效数据
    df = df.sort_values('日期').reset_index(drop=True)
    
    # 更严格的数据过滤逻辑，确保数据质量
    df = df.dropna(subset=['开盘', '收盘', '最高', '最低', '成交量', '成交额'])
    df = df[df['成交量'] > 0].reset_index(drop=True)
    df = df[df['成交额'] > 0].reset_index(drop=True)
    
    # 过滤掉明显异常的数据（如价格为0的情况）
    df = df[(df['开盘'] > 0) & (df['收盘'] > 0) & (df['最高'] > 0) & (df['最低'] > 0)].reset_index(drop=True)
    
    # 确保高价≥低价，开盘和收盘在高低价之间（基本的数据一致性检查）
    df = df[df['最高'] >= df['最低']].reset_index(drop=True)
    df = df[(df['开盘'] >= df['最低']) & (df['开盘'] <= df['最高'])].reset_index(drop=True)
    df = df[(df['收盘'] >= df['最低']) & (df['收盘'] <= df['最高'])].reset_index(drop=True)
    
    # 获取证券名称用于图例
    if symbol_code is None:
        # 如果没有传入symbol_code，尝试从数据中获取
        if '股票代码' in df.columns:
            symbol_code = df['股票代码'].iloc[0]
        else:
            # 对于某些数据源，可能需要从其他列获取代码
            symbol_code = df.iloc[0, 0] if len(df.columns) > 0 else "未知代码"
    
    # 确保symbol_code是字符串格式，并去掉可能的后缀（如.SZ）
    symbol_code = str(symbol_code).split('.')[0]
    
    # 查找证券名称
    # 调试：检查info_df的结构
    print(f"Debug - symbol_code: {symbol_code}")
    print(f"Debug - info_df columns: {info_df.columns.tolist()}")
    print(f"Debug - info_df first few rows:")
    print(info_df.head())
    
    security_name = info_df[info_df["code"] == symbol_code]["name"].values
    security_name = security_name[0] if len(security_name) > 0 else f"未知{security_type}"
    
    print(f"Debug - found security_name: {security_name}")  # 调试信息
    
    # 添加K线图到第一行
    fig.add_trace(go.Candlestick(
        x=df['日期'],
        open=df['开盘'],
        high=df['最高'],
        low=df['最低'],
        close=df['收盘'],
        name=f'{security_name}',  # 使用证券名称
        increasing_line_color='#FF4444',  # 红涨
        decreasing_line_color='#00AA00',  # 绿跌
        increasing_fillcolor='#FF4444',
        decreasing_fillcolor='#00AA00'
    ), row=1, col=1)
    
    # KDAS线条颜色配置
    kdas_colors = {
        'day1': "#FF0000",   # 红色
        'day2': "#0000FF",   # 蓝色  
        'day3': "#00FF00",   # 绿色
        'day4': "#FF00FF",   # 紫色
        'day5': "#FFA500",   # 橙色
    }
    
    # 添加KDAS线条到第一行（与股价共享同一个Y轴）
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            # 过滤掉NaN值
            mask = df[f'KDAS{value}'].notna()
            fig.add_trace(go.Scatter(
                x=df.loc[mask, '日期'],
                y=df.loc[mask, f'KDAS{value}'],
                mode='lines',
                name=f'KDAS {value}',
                line=dict(
                    color=kdas_colors.get(key, "#000000"), 
                    width=2.5,
                    dash='solid'
                ),
                opacity=0.8
            ), row=1, col=1)
    
    # 添加成交量柱状图到第二行
    volume_colors = ['#FF4444' if close >= open else '#00AA00' 
                    for close, open in zip(df['收盘'], df['开盘'])]
    
    fig.add_trace(go.Bar(
        x=df['日期'],
        y=df['成交量'],
        name='成交量',
        marker_color=volume_colors,
        opacity=0.7,
        showlegend=False
    ), row=2, col=1)
    
    # 设置Y轴标题
    fig.update_yaxes(title_text="价格/KDAS (元)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=1)
    
    # 计算当前支撑位和压力位
    current_price = df['收盘'].iloc[-1]
    support_levels = []  # 支撑位（价格下方的KDAS值）
    resistance_levels = []  # 压力位（价格上方的KDAS值）
    
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            # 获取最新的KDAS值
            kdas_series = df[f'KDAS{value}'].dropna()
            if not kdas_series.empty:
                latest_kdas = kdas_series.iloc[-1]
                if latest_kdas < current_price:
                    support_levels.append((latest_kdas, f"支撑位: ¥{latest_kdas:.3f}"))
                elif latest_kdas > current_price:
                    resistance_levels.append((latest_kdas, f"压力位: ¥{latest_kdas:.3f}"))
    
    # 对支撑位和压力位进行排序
    support_levels.sort(key=lambda x: x[0], reverse=True)  # 支撑位从高到低排序
    resistance_levels.sort(key=lambda x: x[0])  # 压力位从低到高排序
    
    # 创建图例文本
    legend_text = []
    legend_text.append(f"📊 当前价格: ¥{current_price:.3f}")
    legend_text.append("━━━━━━━━━━━━━━━━")
    
    if resistance_levels:
        legend_text.append("🔴 压力位:")
        for _, text in resistance_levels:
            legend_text.append(f"  {text}")
    
    if support_levels:
        legend_text.append("🟢 支撑位:")
        for _, text in support_levels:
            legend_text.append(f"  {text}")
    
    if not resistance_levels and not support_levels:
        legend_text.append("暂无明显支撑/压力位")
    
    # 更新整体布局
    fig.update_layout(
        title={
            'text': f"{security_name} ({symbol_code}) - K线走势图与KDAS指标分析",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        height=800,
        xaxis_rangeslider_visible=False,  # 隐藏K线图下方的范围滑块
        showlegend=False,  # 隐藏默认图例
        hovermode='x unified',  # 统一悬停模式
        template='plotly_white',  # 使用白色主题
        annotations=[
            dict(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text="<br>".join(legend_text),
                showarrow=False,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='rgba(0, 0, 0, 0.3)',
                borderwidth=1,
                font=dict(size=11, family="monospace"),
                align="left",
                xanchor="left",
                yanchor="top"
            )
        ]
    )
    
    # 使用官方交易日历配置X轴，精确跳过非交易日
    # 基础配置：隐藏周末
    rangebreaks_config = [
        dict(bounds=["sat", "mon"])  # 隐藏周末
    ]
    
    # 获取数据的日期范围
    start_date = df['日期'].min().date()
    end_date = df['日期'].max().date()
    
    # 使用官方交易日历获取非交易日
    non_trading_dates = get_non_trading_dates(start_date, end_date)
    
    if non_trading_dates:
        rangebreaks_config.append(dict(values=non_trading_dates))
        print(f"🗓️ 应用了 {len(non_trading_dates)} 个非交易日的rangebreaks配置")
    else:
        print("⚠️ 未获取到非交易日数据，仅应用周末配置")
    
    # 应用配置到两个子图
    fig.update_xaxes(rangebreaks=rangebreaks_config, row=1, col=1)
    fig.update_xaxes(rangebreaks=rangebreaks_config, row=2, col=1)
    
    # 设置价格和KDAS的综合Y轴范围
    # 获取价格范围
    price_min = df[['开盘', '收盘', '最高', '最低']].min().min()
    price_max = df[['开盘', '收盘', '最高', '最低']].max().max()
    
    # 获取KDAS范围
    kdas_values = []
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            kdas_values.extend(df[f'KDAS{value}'].dropna().tolist())
    
    # 计算综合范围
    if kdas_values:
        kdas_min, kdas_max = min(kdas_values), max(kdas_values)
        combined_min = min(price_min, kdas_min)
        combined_max = max(price_max, kdas_max)
    else:
        combined_min = price_min
        combined_max = price_max
    
    # 设置Y轴范围，留出10%的余量
    range_span = combined_max - combined_min
    fig.update_yaxes(
        range=[combined_min - range_span * 0.1, combined_max + range_span * 0.1],
        row=1, col=1
    )
    
    return fig

def main():
    st.set_page_config(page_title="KDAS证券分析工具", layout="wide")
    
    st.title("📈 KDAS证券分析工具")
    st.markdown("---")
    
    # 检查是否需要加载完整配置
    load_full_config = st.session_state.get('load_full_config', None)
    if load_full_config:
        st.success(f"✅ 已加载完整配置: {load_full_config['symbol']}")
        # 将配置信息设置到session_state中，用于组件显示
        st.session_state.current_security_type = load_full_config['security_type']
        st.session_state.current_symbol = load_full_config['symbol']
        st.session_state.current_dates = load_full_config['dates']
        # 清除load_full_config标志
        st.session_state.load_full_config = None
    
    # 侧边栏配置
    with st.sidebar:
        st.header("📊 配置参数")
        
        # 证券类型选择 - 如果有当前配置，则使用配置中的类型
        current_security_type = st.session_state.get('current_security_type', None)
        if current_security_type:
            security_type_options = ["股票", "ETF", "指数"]
            default_type_index = security_type_options.index(current_security_type)
        else:
            default_type_index = 0
            
        security_type = st.selectbox(
            "证券类型",
            ["股票", "ETF", "指数"],
            index=default_type_index,
            help="选择要分析的证券类型"
        )
        
        # 根据证券类型加载对应的信息
        if security_type == "股票":
            info_df = load_stock_info()
            default_symbol = "001215"
            help_text = "请输入6位股票代码"
        elif security_type == "ETF":
            info_df = load_etf_info()
            default_symbol = "159915"
            help_text = "请输入6位ETF代码"
        else:  # 指数
            info_df = load_index_info()
            default_symbol = "000001"
            help_text = "请输入6位指数代码"
        
        # 如果有当前配置，使用配置中的代码
        current_symbol = st.session_state.get('current_symbol', None)
        if current_symbol:
            default_symbol = current_symbol
        
        # 证券代码选择
        symbol = st.text_input(f"{security_type}代码", value=default_symbol, help=help_text)
        
        # 检查是否有保存的配置
        saved_config = None
        if symbol:
            saved_config = get_saved_config(symbol, security_type)
            if saved_config:
                st.success(f"💾 找到保存的配置: {saved_config['security_name']}")
                if st.button("🔄 加载保存的日期配置", use_container_width=True):
                    st.session_state.load_saved_config = True
                    st.rerun()
        
        st.subheader("KDAS计算起始日期")
        
        # 使用日期选择器
        default_dates = [
            datetime(2024, 9, 24).date(),
            datetime(2024, 11, 7).date(),
            datetime(2024, 12, 17).date(),
            datetime(2025, 4, 7).date(),
            datetime(2025, 4, 23).date()
        ]
        
                # 如果有当前配置，使用配置中的日期（优先级最高）
        current_dates = st.session_state.get('current_dates', None)
        if current_dates:
            try:
                for i, (key, date_str) in enumerate(current_dates.items()):
                    if i < len(default_dates):  # 确保不超出范围
                        date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                        default_dates[i] = date_obj
            except Exception as e:
                st.warning(f"加载完整配置的日期失败: {e}")
        
        # 如果有保存的配置且用户选择加载，则使用保存的日期（仅当没有当前配置时）
        elif (saved_config and 
            hasattr(st.session_state, 'load_saved_config') and 
            st.session_state.load_saved_config):
            try:
                for i, (key, date_str) in enumerate(saved_config['dates'].items()):
                    date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                    default_dates[i] = date_obj
                st.session_state.load_saved_config = False  # 重置标志
                st.success("✅ 已加载保存的日期配置！")
            except Exception as e:
                st.warning(f"加载保存的日期配置失败: {e}")
        
        input_date = {}
        colors = ["🔴", "🔵", "🟢", "🟣", "🟡"]
        
        for i in range(5):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"{colors[i]} Day{i+1}")
            with col2:
                selected_date = st.date_input(
                    f"日期{i+1}",
                    value=default_dates[i],
                    key=f"date_{i+1}"
                )
                input_date[f'day{i+1}'] = selected_date.strftime('%Y%m%d')
        
        # 分析按钮
        analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)
        
        # 如果当前有加载的配置，显示清除按钮
        if st.session_state.get('current_security_type') or st.session_state.get('current_symbol') or st.session_state.get('current_dates'):
            if st.button("🔄 清除当前配置", use_container_width=True):
                # 清除当前配置
                keys_to_clear = ['current_security_type', 'current_symbol', 'current_dates']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        # 配置管理
        st.markdown("---")
        st.subheader("💾 配置管理")
        
        # 显示已保存的配置
        configs = load_user_configs()
        if configs:
            st.write(f"已保存 {len(configs)} 个配置:")
            
            for config_key, config in configs.items():
                with st.expander(f"{config['security_name']} ({config['symbol']})"):
                    st.write(f"**类型**: {config['security_type']}")
                    st.write(f"**保存时间**: {config['save_time']}")
                    st.write("**日期配置**:")
                    for day_key, date_str in config['dates'].items():
                        try:
                            date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                            st.write(f"  - {day_key}: {date_obj}")
                        except:
                            st.write(f"  - {day_key}: {date_str}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"📋 加载完整配置", key=f"load_full_{config_key}"):
                            # 清除之前的配置状态
                            keys_to_clear = ['current_security_type', 'current_symbol', 'current_dates', 'load_saved_config']
                            for key in keys_to_clear:
                                if key in st.session_state:
                                    del st.session_state[key]
                            
                            # 设置加载标志，在页面重新渲染时会被处理
                            st.session_state.load_full_config = {
                                'security_type': config['security_type'],
                                'symbol': config['symbol'],
                                'dates': config['dates']
                            }
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🗑️ 删除配置", key=f"delete_{config_key}"):
                            if delete_saved_config(config['symbol'], config['security_type']):
                                st.success("配置已删除！")
                                st.rerun()
                            else:
                                st.error("删除配置失败！")
        else:
            st.info("暂无保存的配置")
    
    # 主要内容区域
    if analyze_button:
        try:
            with st.spinner(f"正在获取{security_type}数据..."):
                # 获取证券数据
                data = get_security_data(symbol, input_date, security_type)
                
                if data.empty:
                    st.error(f"未找到该{security_type}的数据，请检查{security_type}代码是否正确。")
                    return
                
                # 计算KDAS
                processed_data = calculate_cumulative_vwap(data, input_date)
                
                # 显示证券基本信息
                security_name = info_df[info_df["code"] == str(symbol)]["name"].values
                security_name = security_name[0] if len(security_name) > 0 else f"未知{security_type}"
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(f"{security_type}名称", security_name)
                with col2:
                    st.metric(f"{security_type}代码", symbol)
                with col3:
                    latest_price = processed_data['收盘'].iloc[-1]
                    st.metric("最新收盘价", f"¥{latest_price:.3f}")
                with col4:
                    if len(processed_data) > 1:
                        price_change = processed_data['收盘'].iloc[-1] - processed_data['收盘'].iloc[-2]
                        st.metric("涨跌", f"¥{price_change:.3f}", delta=f"{(price_change/processed_data['收盘'].iloc[-2]*100):.3f}%")
                    else:
                        st.metric("涨跌", "暂无数据")
                
                st.markdown("---")
                
                # 创建并显示图表
                fig = create_interactive_chart(processed_data, input_date, info_df, security_type, symbol)
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示KDAS数据表
                st.subheader("📋 KDAS数据详情")
                
                # 准备显示的列
                display_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额']
                kdas_cols = [col for col in processed_data.columns if col.startswith('KDAS')]
                display_cols.extend(kdas_cols)
                
                # 只显示最近的数据
                recent_data = processed_data[display_cols].tail(20)
                st.dataframe(recent_data, use_container_width=True)
                
                # 保存当前配置
                if save_current_config(symbol, security_type, input_date, security_name):
                    st.success("✅ 当前配置已自动保存，下次可直接加载！")
                
        except Exception as e:
            st.error(f"分析过程中出现错误: {str(e)}")
            st.info("请检查股票代码是否正确，或稍后重试。")
    
    else:
        # 显示使用说明
        st.info("👈 请在左侧边栏配置参数并点击「开始分析」按钮")
        
        with st.expander("📖 使用说明"):
            st.markdown("""
            ### KDAS指标说明
            KDAS（Key Date Average Settlement）是基于关键日期的累计成交量加权平均价格指标。
            
            ### 使用步骤
            1. 选择证券类型（股票、ETF、指数）
            2. 输入对应的6位证券代码
               - 股票：如 000001、300001、001215等
               - ETF：如 159915、159919、510300等
               - 指数：如 000001（上证指数）、399001（深证成指）等
            3. 选择5个关键的分析日期
            4. 点击「开始分析」按钮
            5. 查看K线图和KDAS指标走势
            
            ### 💾 记忆功能（新增）
            - **自动保存**: 每次分析后会自动保存当前证券代码及其对应的日期配置
            - **智能识别**: 输入之前分析过的证券代码时，会自动提示有保存的配置
            - **部分加载**: 点击"加载保存的日期配置"按钮仅恢复日期设置
            - **完整加载**: 点击"📋 加载完整配置"按钮一键切换证券类型、代码和所有日期
            - **配置重置**: 加载配置后可点击"🔄 清除当前配置"按钮恢复默认状态
            - **配置管理**: 在侧边栏底部可以查看和删除已保存的所有配置
            - **数据持久化**: 配置信息保存在本地文件中，重启应用也不会丢失
            
            ### 图表说明
            - **K线图**: 显示证券的开高低收价格走势
            - **KDAS线**: 不同颜色表示从不同日期开始计算的KDAS值
            - **成交量**: 显示每日的成交量情况
            - **图例**: 位于图表左上角，可以点击控制显示/隐藏
            - **时间轴优化**: 使用新浪财经官方交易日历数据，精确跳过非交易日，确保x轴连续显示
            
            ### 支持的证券类型
            - **股票**: A股上市公司股票
            - **ETF**: 交易型开放式指数基金
            - **指数**: 沪深各类股票指数
            """)

if __name__ == "__main__":
    # 检测是否通过streamlit运行
    try:
        import streamlit.runtime.scriptrunner.script_run_context as ctx
        if ctx.get_script_run_ctx() is None:
            # 不是通过streamlit运行
            print("❌ 请使用以下命令之一来运行应用：")
            print()
            print("方法一（推荐）：")
            print("   python run_app.py")
            print()
            print("方法二：")
            print("   streamlit run KDAS.py")
            print()
            print("⚠️  不要直接使用 'python KDAS.py' 运行！")
            exit(1)
    except ImportError:
        pass
    
    main()