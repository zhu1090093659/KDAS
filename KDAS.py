import os
import akshare as ak
import pandas as pd
from datetime import datetime, date, timedelta
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import json
import re

# 导入AI顾问模块
try:
    from kdas_ai_advisor import get_ai_advisor
    AI_ADVISOR_AVAILABLE = True
except ImportError:
    AI_ADVISOR_AVAILABLE = False
    st.warning("⚠️ AI智能推荐功能需要安装openai库: pip install openai")

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

def save_api_key(api_key, model_name):
    """保存API密钥到配置文件"""
    configs = load_user_configs()
    
    # 确保存在全局设置部分
    if 'global_settings' not in configs:
        configs['global_settings'] = {}
    
    # 保存API密钥和默认模型
    configs['global_settings']['api_key'] = api_key
    configs['global_settings']['default_model'] = model_name
    configs['global_settings']['save_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return save_user_configs(configs)

def save_ai_analysis_setting(enabled):
    """保存AI分析开关设置"""
    configs = load_user_configs()
    
    # 确保存在全局设置部分
    if 'global_settings' not in configs:
        configs['global_settings'] = {}
    
    # 保存AI分析开关设置
    configs['global_settings']['ai_analysis_enabled'] = enabled
    configs['global_settings']['save_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return save_user_configs(configs)

def load_ai_analysis_setting():
    """加载AI分析开关设置"""
    configs = load_user_configs()
    global_settings = configs.get('global_settings', {})
    return global_settings.get('ai_analysis_enabled', False)  # 默认关闭

def load_api_key():
    """从配置文件加载API密钥"""
    configs = load_user_configs()
    global_settings = configs.get('global_settings', {})
    api_key = global_settings.get('api_key', '')
    default_model = global_settings.get('default_model', 'deepseek-r1')
    return api_key, default_model

def delete_api_key():
    """删除保存的API密钥"""
    configs = load_user_configs()
    if 'global_settings' in configs:
        if 'api_key' in configs['global_settings']:
            del configs['global_settings']['api_key']
        if 'default_model' in configs['global_settings']:
            del configs['global_settings']['default_model']
        if 'ai_analysis_enabled' in configs['global_settings']:
            del configs['global_settings']['ai_analysis_enabled']
        # 如果global_settings为空，则删除整个section
        if not configs['global_settings']:
            del configs['global_settings']
        return save_user_configs(configs)
    return False

def _format_analysis_text(analysis_text):
    """格式化AI分析文本，使其更适合Streamlit显示"""
    import re
    import json
    
    if not analysis_text or not analysis_text.strip():
        return "暂无分析内容"
    
    # 尝试从文本中提取JSON部分
    json_data = _extract_json_from_text(analysis_text)
    
    if json_data:
        # 如果成功提取并解析JSON，则格式化展示
        return _format_json_analysis(json_data)
    else:
        # 如果不是JSON格式，使用原有的文本格式化方法
        return _format_plain_text_analysis(analysis_text)

def _extract_json_from_text(text):
    """从文本中提取JSON部分并解析为字典"""
    import re
    import json
    
    try:
        # 方法1：尝试找到被```json包围的JSON
        json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            return json.loads(json_str)
        
        # 方法2：尝试找到大括号包围的JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group().strip()
            return json.loads(json_str)
        
        # 方法3：尝试直接解析整个文本
        return json.loads(text.strip())
        
    except (json.JSONDecodeError, AttributeError):
        return None

def _format_json_analysis(json_data):
    """格式化JSON格式的分析结果"""
    if not isinstance(json_data, dict):
        return "分析结果格式错误"
    
    formatted_content = []
    
    # 定义字段映射和图标
    field_mapping = {
        '状态': ('📊', 'KDAS状态分析'),
        '多空力量分析': ('⚖️', '多空力量对比'),
        '趋势方向判断': ('📈', '趋势方向判断'),
        '交易建议': ('💡', '交易策略建议'),
        '风险提示': ('⚠️', '风险评估提示'),
        '置信度': ('🎯', '分析置信度')
    }
    
    # 按预定义顺序展示字段
    for field_key, (icon, title) in field_mapping.items():
        if field_key in json_data:
            content = json_data[field_key]
            if content and str(content).strip():
                # 格式化内容
                formatted_content.append(f"#### {icon} {title}")
                formatted_content.append("")
                
                # 应用文本样式
                styled_content = _apply_text_styling(str(content))
                formatted_content.append(styled_content)
                formatted_content.append("")  # 添加空行分隔
    
    # 处理其他未映射的字段
    for key, value in json_data.items():
        if key not in field_mapping and value and str(value).strip():
            formatted_content.append(f"#### 🔸 {key}")
            formatted_content.append("")
            styled_content = _apply_text_styling(str(value))
            formatted_content.append(styled_content)
            formatted_content.append("")
    
    return '\n'.join(formatted_content)

def _format_plain_text_analysis(analysis_text):
    """格式化普通文本格式的分析结果（保留原有逻辑）"""
    import re
    
    # 首先处理整体结构
    formatted_content = []
    
    # 按行分割并重新组织
    lines = analysis_text.split('\n')
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_section:
                # 处理当前积累的段落
                section_text = ' '.join(current_section).strip()
                if section_text:
                    formatted_content.append(_format_paragraph(section_text))
                current_section = []
            continue
        
        current_section.append(line)
    
    # 处理最后一个段落
    if current_section:
        section_text = ' '.join(current_section).strip()
        if section_text:
            formatted_content.append(_format_paragraph(section_text))
    
    # 合并所有内容
    result = '\n\n'.join(formatted_content)
    
    # 全局样式优化
    result = _apply_text_styling(result)
    
    return result

def _format_paragraph(text):
    """格式化单个段落"""
    import re
    
    if not text.strip():
        return ""
    
    # 处理主要章节标题（如：1. **当前KDAS状态判断**）
    main_section_match = re.match(r'^(\d+)\.\s*\*\*(.*?)\*\*[:：]?(.*)', text)
    
    if main_section_match:
        num = main_section_match.group(1)
        title = main_section_match.group(2).strip()
        content = main_section_match.group(3).strip()
        
        icons = {
            '1': '📊', '2': '⚖️', '3': '📈', 
            '4': '💡', '5': '🎯', '6': '⚠️'
        }
        icon = icons.get(num, '🔸')
        
        result = f"#### {icon} {num}. {title}\n"
        if content:
            result += f"\n{content}"
        return result
    
    # 处理子标题（如：**多空力量分析**）
    subtitle_match = re.match(r'^\*\*(.*?)\*\*[:：]?(.*)', text)
    if subtitle_match:
        title = subtitle_match.group(1).strip()
        content = subtitle_match.group(2).strip()
        result = f"**🔸 {title}**"
        if content:
            result += f"\n\n{content}"
        return result
    
    # 处理引用内容
    if text.startswith('"') and text.endswith('"'):
        return f"> {text[1:-1]}"
    
    # 处理列表项
    if text.startswith('- '):
        return f"• {text[2:]}"
    
    # 处理普通段落
    return text

def _apply_text_styling(text):
    """应用文本样式优化"""
    
    # 关键词高亮
    styling_rules = [
        ('多头', '🟢 **多头**'),
        ('空头', '🔴 **空头**'),
        ('支撑位', '🟢 **支撑位**'),
        ('压力位', '🔴 **压力位**'),
        ('阻力位', '🔴 **阻力位**'),
        ('突破', '⚡ **突破**'),
        ('趋势确认', '✅ **趋势确认**'),
        ('趋势反转', '🔄 **趋势反转**'),
        ('情绪宣泄', '😱 **情绪宣泄**'),
        ('震荡', '📊 **震荡**'),
        ('整理', '⏸️ **整理**'),
        ('风险', '⚠️ **风险**'),
        ('建议', '💡 **建议**'),
        ('策略', '🎯 **策略**'),
        ('关键位', '🔑 **关键位**'),
        ('收敛', '📐 **收敛**'),
        ('发散', '📏 **发散**'),
        ('观望', '👀 **观望**'),
        ('入场', '🚀 **入场**'),
        ('止损', '🛑 **止损**'),
        ('止盈', '✨ **止盈**'),
        ('KDAS', '📊 **KDAS**'),
        ('均线', '📈 **均线**'),
        ('多空力量', '⚖️ **多空力量**'),
        ('趋势行进', '📈 **趋势行进**'),
        ('趋势衰竭', '📉 **趋势衰竭**'),
        ('市场一致性', '🎯 **市场一致性**'),
        ('情绪积累', '📊 **情绪积累**'),
        ('盘整', '📊 **盘整**'),
        ('强势', '💪 **强势**'),
        ('弱势', '📉 **弱势**'),
        ('高位', '⬆️ **高位**'),
        ('低位', '⬇️ **低位**')
    ]
    
    for old, new in styling_rules:
        # 只替换独立的词，避免重复替换
        text = re.sub(f'(?<!\\*){re.escape(old)}(?!\\*)', new, text)
    
    return text

def save_multi_chart_config(global_dates, securities):
    """保存多图看板配置"""
    configs = load_user_configs()
    
    # 确保存在全局设置部分
    if 'global_settings' not in configs:
        configs['global_settings'] = {}
    
    # 保存多图看板配置
    configs['global_settings']['multi_chart_config'] = {
        'global_dates': [date.isoformat() for date in global_dates],
        'securities': securities,
        'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return save_user_configs(configs)

def load_multi_chart_config():
    """加载多图看板配置"""
    configs = load_user_configs()
    global_settings = configs.get('global_settings', {})
    multi_config = global_settings.get('multi_chart_config', None)
    
    if multi_config:
        # 转换日期格式
        global_dates = [datetime.fromisoformat(date_str).date() for date_str in multi_config['global_dates']]
        securities = multi_config['securities']
        return global_dates, securities
    
    # 返回默认配置
    default_dates = [
        datetime(2024, 9, 24).date(),
        datetime(2024, 11, 7).date(),
        datetime(2024, 12, 17).date(),
        datetime(2025, 4, 7).date(),
        datetime(2025, 4, 23).date()
    ]
    
    default_securities = [
        {'type': '股票', 'symbol': '001215', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': 'ETF', 'symbol': '159915', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': '指数', 'symbol': '000001', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': '股票', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': 'ETF', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': '指数', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
    ]
    
    return default_dates, default_securities

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
    try:
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
            
            # 转换start_date为Timestamp以便比较
            start_date_ts = pd.to_datetime(start_date)
            if not (df['日期'] == start_date_ts).any():
                df = api_func()
                if not df.empty:
                    # 确保日期列格式正确
                    df['日期'] = pd.to_datetime(df['日期'])
                    df.to_csv(file_path, index=False)
            else:
                # 检查是否需要更新数据 - 更安全的日期比较
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
        # 添加更详细的错误信息
        import traceback
        error_details = traceback.format_exc()
        raise Exception(f"get_security_data函数执行失败: {str(e)}\n详细错误:\n{error_details}")

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
    # print(f"Debug - symbol_code: {symbol_code}")
    # print(f"Debug - info_df columns: {info_df.columns.tolist()}")
    # print(f"Debug - info_df first few rows:")
    # print(info_df.head())
    
    security_name = info_df[info_df["code"] == symbol_code]["name"].values
    security_name = security_name[0] if len(security_name) > 0 else f"未知{security_type}"
    
    # print(f"Debug - found security_name: {security_name}")  # 调试信息
    
    # 添加K线图到第一行
    fig.add_trace(go.Candlestick(
        x=df['日期'],
        open=df['开盘'],
        high=df['最高'],
        low=df['最低'],
        close=df['收盘'],
        name=f'{security_name}',
        increasing_line_color='#FF4444',
        decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF4444',
        decreasing_fillcolor='#00AA00',
        showlegend=False
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
                name=f'D{key[-1]}',
                line=dict(color=kdas_colors.get(key, "#000000"), width=2, dash='solid'),
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

def create_mini_chart(df, input_date, info_df, security_type="股票", symbol_code=None):
    """创建紧凑型交互式图表，用于多图看板"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=(None, None), # No subplot titles
        row_heights=[0.7, 0.3]
    )
    
    df = df.sort_values('日期').reset_index(drop=True)
    df = df.dropna(subset=['开盘', '收盘', '最高', '最低', '成交量', '成交额'])
    df = df[df['成交量'] > 0].reset_index(drop=True)
    df = df[(df['开盘'] > 0) & (df['收盘'] > 0) & (df['最高'] > 0) & (df['最低'] > 0)].reset_index(drop=True)
    df = df[df['最高'] >= df['最低']].reset_index(drop=True)

    symbol_code = str(symbol_code).split('.')[0]
    security_name_series = info_df[info_df["code"] == symbol_code]["name"]
    security_name = security_name_series.values[0] if len(security_name_series) > 0 else f"未知{security_type}"
    
    fig.add_trace(go.Candlestick(
        x=df['日期'],
        open=df['开盘'],
        high=df['最高'],
        low=df['最低'],
        close=df['收盘'],
        name=f'{security_name}',
        increasing_line_color='#FF4444',
        decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF4444',
        decreasing_fillcolor='#00AA00',
        showlegend=False
    ), row=1, col=1)
    
    kdas_colors = {
        'day1': "#FF0000", 'day2': "#0000FF", 'day3': "#00FF00",
        'day4': "#FF00FF", 'day5': "#FFA500",
    }
    
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            mask = df[f'KDAS{value}'].notna()
            fig.add_trace(go.Scatter(
                x=df.loc[mask, '日期'],
                y=df.loc[mask, f'KDAS{value}'],
                mode='lines',
                name=f'D{key[-1]}',
                line=dict(color=kdas_colors.get(key, "#000000"), width=2, dash='solid'),
                opacity=0.8
            ), row=1, col=1)
    
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
    
    fig.update_layout(
        title={
            'text': f"{security_name} ({symbol_code})",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 14}
        },
        height=400,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=40, r=20, t=70, b=40),
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
                font=dict(size=9, family="monospace"),  # 使用更小的字体以适应小图
                align="left",
                xanchor="left",
                yanchor="top"
            )
        ]
    )
    
    start_date, end_date = df['日期'].min().date(), df['日期'].max().date()
    non_trading_dates = get_non_trading_dates(start_date, end_date)
    
    rangebreaks_config = [dict(bounds=["sat", "mon"])]
    if non_trading_dates:
        rangebreaks_config.append(dict(values=non_trading_dates))
    
    fig.update_xaxes(rangebreaks=rangebreaks_config)
    fig.update_yaxes(title_text=None, row=1, col=1)
    fig.update_yaxes(title_text=None, row=2, col=1)
    
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
    
    with st.sidebar:
        st.header("模式选择")
        app_mode = st.radio(
            "选择分析模式",
            ("单图精细分析", "多图概览看板"),
            key='app_mode_selection',
            horizontal=True,
        )
        st.markdown("---")

    if app_mode == "单图精细分析":
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
            
                            # AI智能推荐功能
            if AI_ADVISOR_AVAILABLE and symbol:
                st.markdown("#### 🤖 AI智能推荐")
                
                # 加载保存的API密钥和模型配置
                saved_api_key, saved_model = load_api_key()
                
                # AI分析开关
                ai_analysis_enabled = load_ai_analysis_setting()
                ai_enabled_checkbox = st.checkbox(
                    "🔮 启用AI智能分析", 
                    value=ai_analysis_enabled,
                    help="开启后将在右侧显示AI分析报告"
                )
                
                # 保存AI分析开关设置
                if ai_enabled_checkbox != ai_analysis_enabled:
                    save_ai_analysis_setting(ai_enabled_checkbox)
                
                # API密钥配置
                api_key_input = st.text_input(
                    "AI API密钥", 
                    value=saved_api_key,  # 使用保存的API密钥作为默认值
                    type="password", 
                    help="输入您的AI API密钥以使用AI智能推荐功能",
                    placeholder="sk-..."
                )
                
                # 获取当前模型列表并确定默认选择
                model_options = ["deepseek-r1", "gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-03-25"]
                default_model_index = 0
                if saved_model in model_options:
                    default_model_index = model_options.index(saved_model)
                
                # AI模型选择
                ai_model = st.selectbox(
                    "AI模型选择",
                    model_options,
                    index=default_model_index,
                    help="选择要使用的AI模型"
                )
                
                # API密钥保存/删除按钮
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 保存配置", help="保存API密钥和模型选择，下次无需重新输入"):
                        if api_key_input.strip():
                            if save_api_key(api_key_input.strip(), ai_model):
                                st.success("✅ 配置已保存！")
                            else:
                                st.error("❌ 保存失败，请重试")
                        else:
                            st.warning("⚠️ 请先输入API密钥")
                
                with col2:
                    if saved_api_key and st.button("🗑️ 清除配置", help="删除保存的API密钥"):
                        if delete_api_key():
                            st.success("✅ 配置已清除！")
                            st.rerun()  # 刷新页面以清除输入框
                        else:
                            st.error("❌ 清除失败，请重试")
                
                if api_key_input:
                    os.environ['OPENAI_API_KEY'] = api_key_input
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    ai_recommend_btn = st.button(
                        "🧠 AI智能推荐日期", 
                        help="基于技术分析和KDAS体系原理智能推荐最佳日期",
                        use_container_width=True,
                        disabled=not ai_enabled_checkbox  # 只有启用AI分析时才能使用
                    )
                with col2:
                    show_analysis = st.checkbox("显示分析", help="显示详细的技术分析过程")
                
                # 如果AI分析未启用，显示提示
                if not ai_enabled_checkbox:
                    st.info("💡 请先勾选上方「🔮 启用AI智能分析」选项以使用AI推荐功能")
                
                # 处理AI推荐
                if ai_recommend_btn:
                    # 清除上一次的AI推荐结果，避免混淆
                    for key in ['ai_recommended_dates', 'ai_reasoning', 'ai_confidence']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    if not api_key_input and not os.getenv('OPENAI_API_KEY'):
                        st.error("⚠️ 请先配置AI API密钥")
                    else:
                        with st.spinner("🤖 AI正在分析技术数据并推荐日期..."):
                            try:
                                # 获取数据进行分析
                                st.info("正在获取数据进行分析...")
                                temp_dates = {f'day{i+1}': (datetime.now() - timedelta(days=30*i)).strftime('%Y%m%d') for i in range(5)}
                                st.info(f"正在获取数据: {temp_dates}")
                                analysis_data = get_security_data(symbol, temp_dates, security_type)
                                st.info(f"数据获取完成: {analysis_data}")
                                if not analysis_data.empty:
                                    # 获取证券名称
                                    security_name = info_df[info_df["code"] == str(symbol)]["name"].values
                                    security_name = security_name[0] if len(security_name) > 0 else f"未知{security_type}"
                                    
                                    # 调用AI顾问（传入用户选择的模型）
                                    advisor = get_ai_advisor(api_key_input, ai_model)
                                    if advisor:
                                        result = advisor.generate_kdas_recommendation(
                                            analysis_data, symbol, security_name, security_type
                                        )
                                        
                                        if result['success']:
                                            st.success("✅ AI推荐完成！")
                                            # 保存推荐日期到session_state，然后重新运行以显示结果
                                            st.session_state.ai_recommended_dates = result['dates']
                                            st.session_state.ai_reasoning = result['reasoning']
                                            st.session_state.ai_confidence = result.get('confidence', 'medium')
                                            st.rerun()
                                        
                                        else:
                                            st.error(f"❌ AI推荐失败: {result['error']}")
                                            if 'fallback_dates' in result and result['fallback_dates']:
                                                st.info("💡 使用智能备用日期方案")
                                                st.session_state.ai_recommended_dates = result['fallback_dates']
                                                # 使用备用方案也需要重新运行
                                                st.rerun()
                                    else:
                                        st.error("❌ 无法初始化AI顾问，请检查API密钥")
                                else:
                                    st.error("❌ 无法获取数据进行分析")
                                    
                            except Exception as e:
                                st.error(f"❌ AI推荐过程出现错误: {str(e)}")
                                st.info("💡 建议检查网络连接和API密钥配置")
                    
                # 如果session_state中存在AI推荐的日期，则显示它们及应用按钮
                if 'ai_recommended_dates' in st.session_state:
                    st.markdown("---")
                    confidence_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠'}
                    confidence = st.session_state.get('ai_confidence', 'medium')
                    
                    st.info(f"**AI模型**: {ai_model}")
                    st.info(f"**推荐置信度**: {confidence_emoji.get(confidence, '🟡')} {confidence.upper()}")
                    st.info(f"**推荐日期**: {st.session_state.ai_recommended_dates}")
                    
                    if show_analysis and 'ai_reasoning' in st.session_state:
                        with st.expander("📊 详细分析过程"):
                            st.markdown(f"**{ai_model} 分析理由:**")
                            st.text(st.session_state.ai_reasoning)
                    
                    # 应用推荐按钮
                    if st.button("📅 应用AI推荐日期", type="primary", use_container_width=True):
                        st.session_state.apply_ai_dates = True
                        st.rerun()

                st.markdown("---")
            
            # 使用日期选择器
            default_dates = [
                datetime(2024, 9, 24).date(),
                datetime(2024, 11, 7).date(),
                datetime(2024, 12, 17).date(),
                datetime(2025, 4, 7).date(),
                datetime(2025, 4, 23).date()
            ]
            
            # 检查是否需要应用AI推荐日期（最高优先级）
            if hasattr(st.session_state, 'apply_ai_dates') and st.session_state.apply_ai_dates:
                ai_dates = st.session_state.get('ai_recommended_dates', [])
                if ai_dates and len(ai_dates) >= 5:
                    try:
                        for i, date_str in enumerate(ai_dates[:5]):
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            # 直接设置到session_state中，不设置default_dates避免冲突
                            st.session_state[f"date_{i+1}"] = date_obj
                        
                        # 清除可能干扰的配置状态
                        if 'current_dates' in st.session_state:
                            del st.session_state['current_dates']
                        
                        # 设置标志表示正在使用AI推荐日期，防止被其他配置覆盖
                        st.session_state.using_ai_dates = True
                        st.session_state.apply_ai_dates = False  # 重置标志
                        st.success("✅ 已应用AI推荐日期！")
                    except Exception as e:
                        st.warning(f"应用AI推荐日期失败: {e}")
            
            # 如果有当前配置，使用配置中的日期（但不要覆盖AI推荐的日期）
            elif st.session_state.get('current_dates') and not st.session_state.get('using_ai_dates', False):
                current_dates = st.session_state.current_dates
                try:
                    for i, (key, date_str) in enumerate(current_dates.items()):
                        if i < len(default_dates):  # 确保不超出范围
                            date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                            # 直接设置到session_state中
                            st.session_state[f"date_{i+1}"] = date_obj
                except Exception as e:
                    st.warning(f"加载完整配置的日期失败: {e}")
            
            # 如果有保存的配置且用户选择加载，则使用保存的日期（但不要覆盖AI推荐的日期）
            elif (saved_config and 
                hasattr(st.session_state, 'load_saved_config') and 
                st.session_state.load_saved_config and
                not st.session_state.get('using_ai_dates', False)):
                try:
                    for i, (key, date_str) in enumerate(saved_config['dates'].items()):
                        date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                        # 直接设置到session_state中
                        st.session_state[f"date_{i+1}"] = date_obj
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
                    # 使用session_state中的值，如果不存在则使用默认值
                    date_key = f"date_{i+1}"
                    if date_key not in st.session_state:
                        st.session_state[date_key] = default_dates[i]
                    
                    # 获取当前日期值（用于检测用户手动更改）
                    current_stored_date = st.session_state.get(date_key)
                    
                    selected_date = st.date_input(
                        f"日期{i+1}",
                        key=f"date_{i+1}"
                    )
                    
                    # 如果用户手动更改了日期，清除AI推荐状态
                    if (st.session_state.get('using_ai_dates', False) and 
                        current_stored_date and 
                        selected_date != current_stored_date):
                        st.session_state.using_ai_dates = False
                    
                    input_date[f'day{i+1}'] = selected_date.strftime('%Y%m%d')
            
            # 分析按钮
            analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)
            
            # 如果当前有加载的配置，显示清除按钮
            if st.session_state.get('current_security_type') or st.session_state.get('current_symbol') or st.session_state.get('current_dates') or st.session_state.get('using_ai_dates'):
                if st.button("🔄 清除当前配置", use_container_width=True):
                    # 清除当前配置
                    keys_to_clear = [
                        'current_security_type', 'current_symbol', 'current_dates',
                        'ai_recommended_dates', 'ai_reasoning', 'ai_confidence', 'using_ai_dates'
                    ]
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    # 同时清除日期选择器的session_state值，让它们回到默认状态
                    for i in range(5):
                        date_key = f"date_{i+1}"
                        if date_key in st.session_state:
                            del st.session_state[date_key]
                            
                    st.rerun()
            
            # 配置管理
            st.markdown("---")
            st.subheader("💾 配置管理")
            
            # 显示全局设置状态
            configs = load_user_configs()
            global_settings = configs.get('global_settings', {})
            if global_settings:
                with st.expander("⚙️ 全局设置"):
                    if 'ai_analysis_enabled' in global_settings:
                        enabled_status = "✅ 已启用" if global_settings['ai_analysis_enabled'] else "❌ 已禁用"
                        st.write(f"**AI智能分析**: {enabled_status}")
                    if 'api_key' in global_settings:
                        masked_key = global_settings['api_key'][:8] + "..." + global_settings['api_key'][-4:] if len(global_settings['api_key']) > 12 else "***"
                        st.write(f"**API密钥**: {masked_key}")
                    if 'default_model' in global_settings:
                        st.write(f"**默认AI模型**: {global_settings['default_model']}")
                    if 'save_time' in global_settings:
                        st.write(f"**保存时间**: {global_settings['save_time']}")
            
            # 显示已保存的配置
            security_configs = {k: v for k, v in configs.items() if k != 'global_settings'}
            if security_configs:
                st.write(f"已保存 {len(security_configs)} 个证券配置:")
                
                for config_key, config in security_configs.items():
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
                                
                                # 清除日期选择器的session_state值
                                for i in range(5):
                                    date_key = f"date_{i+1}"
                                    if date_key in st.session_state:
                                        del st.session_state[date_key]
                                
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
                st.info("暂无保存的证券配置")
        
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
                    
                    # 创建布局：左侧图表，右侧AI分析
                    col_chart, col_analysis = st.columns([3, 2])  # 调整比例，给分析面板更多空间
                    
                    with col_chart:
                        # 创建并显示图表
                        fig = create_interactive_chart(processed_data, input_date, info_df, security_type, symbol)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col_analysis:
                        st.subheader("🤖 KDAS智能分析")
                        
                        # AI分析功能
                        if AI_ADVISOR_AVAILABLE:
                            # 从侧边栏获取API密钥和模型配置
                            saved_api_key, saved_model = load_api_key()
                            ai_analysis_enabled = load_ai_analysis_setting()
                            
                            if ai_analysis_enabled and saved_api_key:  # 只有在开启AI分析且有API密钥时才分析
                                # 自动进行KDAS状态分析
                                with st.spinner("🧠 AI正在分析KDAS状态..."):
                                    try:
                                        advisor = get_ai_advisor(saved_api_key, saved_model)
                                        if advisor:
                                            analysis_result = advisor.analyze_kdas_state(
                                                processed_data, input_date, symbol, security_name, security_type
                                            )
                                            
                                            if analysis_result['success']:
                                                st.success(f"✅ 分析完成 ({analysis_result['timestamp']})")
                                                
                                                # 显示分析结果，优化样式
                                                st.markdown("""
                                                <div style="
                                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                                    padding: 1rem;
                                                    border-radius: 10px;
                                                    margin-bottom: 1rem;
                                                    color: white;
                                                    text-align: center;
                                                ">
                                                    <h3 style="margin: 0; color: white;">🤖 KDAS智能分析</h3>
                                                    <p style="margin: 5px 0 0 0; opacity: 0.9;">AI模型: {}</p>
                                                </div>
                                                """.format(saved_model), unsafe_allow_html=True)
                                                
                                                # 使用容器来组织分析内容
                                                with st.container():
                                                    # 格式化并显示分析结果
                                                    analysis_text = analysis_result['analysis']
                                                    formatted_analysis = _format_analysis_text(analysis_text)
                                                    
                                                    # 使用expander让用户可以收起/展开
                                                    with st.expander("📈 查看详细分析报告", expanded=True):
                                                        st.markdown(formatted_analysis, unsafe_allow_html=True)
                                            else:
                                                st.error(f"❌ 分析失败: {analysis_result['error']}")
                                                st.markdown(analysis_result['analysis'])
                                        else:
                                            st.error("❌ 无法初始化AI顾问")
                                    except Exception as e:
                                        st.error(f"❌ 分析过程出现错误: {str(e)}")
                            
                            elif not ai_analysis_enabled:  # AI分析未启用
                                st.info("💡 **启用KDAS智能分析**")
                                st.markdown("勾选左侧边栏「🔮 启用AI智能分析」选项，此处将自动显示专业的KDAS状态分析报告，包括：")
                                st.markdown("- 📊 当前KDAS状态判断")
                                st.markdown("- ⚖️ 多空力量分析")
                                st.markdown("- 📈 趋势方向判断")
                                st.markdown("- 💡 交易策略建议")
                                st.markdown("- 🎯 关键位识别")
                                st.markdown("- ⚠️ 风险提示")
                                
                                st.info("💡 在左侧边栏勾选「🔮 启用AI智能分析」即可开启")
                            
                            elif not saved_api_key:  # 没有保存的API密钥
                                st.info("💡 **配置AI API密钥**")
                                st.markdown("您已启用AI智能分析，但还需要配置API密钥才能使用：")
                                st.markdown("- 📊 当前KDAS状态判断")
                                st.markdown("- ⚖️ 多空力量分析")
                                st.markdown("- 📈 趋势方向判断")
                                st.markdown("- 💡 交易策略建议")
                                st.markdown("- 🎯 关键位识别")
                                st.markdown("- ⚠️ 风险提示")
                                
                                st.warning("⚠️ 需要先在左侧边栏的AI智能推荐区域配置API密钥")
                            
                            else:  # 其他情况（应该不会到达这里）
                                st.error("❌ 未知错误，请检查AI配置")
                        
                        else:
                            st.warning("⚠️ AI智能分析功能需要安装openai库")
                            st.info("请运行: pip install openai")
                    
                    # # 显示KDAS数据表
                    # st.subheader("📋 KDAS数据详情")
                    
                    # # 准备显示的列
                    # display_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额']
                    # kdas_cols = [col for col in processed_data.columns if col.startswith('KDAS')]
                    # display_cols.extend(kdas_cols)
                    
                    # # 只显示最近的数据
                    # recent_data = processed_data[display_cols].tail(20)
                    # st.dataframe(recent_data, use_container_width=True)
                    
                    # 保存当前配置
                    if not st.session_state.get('using_ai_dates', False):
                        # 正常情况下的自动保存
                        if save_current_config(symbol, security_type, input_date, security_name):
                            st.success("✅ 当前配置已自动保存，下次可直接加载！")
                    else:
                        # 使用AI推荐日期时的手动保存选项
                        col_save1, col_save2 = st.columns(2)
                        with col_save1:
                            st.info("💡 当前使用AI推荐日期")
                        with col_save2:
                            if st.button("💾 保存AI推荐配置", help="将当前的AI推荐日期保存为配置"):
                                if save_current_config(symbol, security_type, input_date, security_name):
                                    st.success("✅ AI推荐配置已保存！")
                                    # 清除AI推荐状态，允许正常使用保存的配置
                                    st.session_state.using_ai_dates = False
                                else:
                                    st.error("❌ 保存失败，请重试")
                    
            except Exception as e:
                st.error(f"分析过程中出现错误: {str(e)}")
                st.info("请检查股票代码是否正确，或稍后重试。")
        
        else:
            # 显示使用说明
            st.info("👈 请在左侧边栏配置参数并点击「开始分析」按钮")
            
            with st.expander("📖 使用说明"):
                st.markdown("""
                ### KDAS指标说明
                KDAS（Key Date Average Settlement）是基于关键日期的累计成交量加权平均价格指标。作者： 叙市 （全网同名）
                
                ### 使用步骤
                1. 选择证券类型（股票、ETF、指数）
                2. 输入对应的6位证券代码
                   - 股票：如 000001、300001、001215等
                   - ETF：如 159915、159919、510300等
                   - 指数：如 000001（上证指数）、399001（深证成指）等
                3. **(可选)** 勾选「🔮 启用AI智能分析」并配置API密钥以使用AI功能
                4. **🤖 AI智能推荐（推荐）** 或 手动选择5个关键的分析日期
                5. 点击「开始分析」按钮
                6. 查看K线图、KDAS指标走势和AI分析报告
                
                ### 🤖 AI智能功能（全新升级）
                
                #### 📅 智能日期推荐
                - **多模型支持**: 支持DeepSeek-R1、Gemini-2.5等多种先进AI模型
                - **智能分析**: 基于大语言模型分析证券的技术指标、价格趋势、成交量等数据
                - **专业推荐**: 遵循KDAS交易体系原理，推荐最佳的关键日期
                - **技术依据**: 识别重要的价格突破点、趋势转折点、异常成交量日期等
                - **降低门槛**: 新手用户无需深入了解技术分析，即可获得专业的日期配置
                
                #### 📊 KDAS状态智能分析（新增）
                - **实时分析**: 基于KDAS交易体系自动分析当前市场状态
                - **四种状态识别**: 趋势行进、趋势衰竭、震荡状态、整理状态的智能判断
                - **多空力量分析**: 分析当前多空力量对比和价格与KDAS系统的位置关系
                - **趋势方向判断**: 基于KDAS系统判断当前趋势方向和强度
                - **交易策略建议**: 根据KDAS体系给出具体的交易策略建议
                - **关键位识别**: 智能识别当前的关键支撑和压力位
                - **风险提示**: 基于当前状态的风险评估和注意事项
                - **专业解读**: 用易懂的语言解释复杂的技术分析结果
                
                #### 🔧 配置管理
                - **🔮 AI分析开关**: 可选择性启用/禁用AI智能分析功能，默认关闭
                - **API配置**: 需要配置AI API密钥（sk-开头的密钥）
                - **模型选择**: 可根据需求选择不同的AI模型进行分析
                - **置信度**: AI会评估推荐的置信度（高/中/低）
                - **备用方案**: 当AI推荐失败时，自动提供智能备用日期方案
                - **💾 配置记忆**: 点击"保存配置"按钮可保存API密钥和模型选择，刷新页面不会丢失
                - **🔒 本地存储**: 所有配置安全保存在本地配置文件中，仅您可以访问
                
                ### 🔧 支持的AI模型
                - **deepseek-r1**: DeepSeek推理模型，逻辑推理能力强
                - **gemini-2.5-flash-preview-05-20**: Google Gemini快速版本，响应速度快
                - **gemini-2.5-pro-preview-03-25**: Google Gemini专业版本，分析更深入
                
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
                - **智能分析面板**: 右侧显示AI实时分析的KDAS状态和交易建议
                - **布局优化**: 左侧图表占2/3，右侧分析面板占1/3，信息展示更高效
                
                ### 支持的证券类型
                - **股票**: A股上市公司股票
                - **ETF**: 交易型开放式指数基金
                - **指数**: 沪深各类股票指数
                """)
    
    else: # 多图概览看板
        with st.sidebar:
            st.header("📊 多图看板配置")
            st.subheader("全局KDAS计算起始日期")

            # 定义全局日期和证券配置 - 从保存的配置中加载
            if 'multi_chart_global_dates' not in st.session_state or 'multi_securities' not in st.session_state:
                # 加载保存的配置
                saved_dates, saved_securities = load_multi_chart_config()
                st.session_state.multi_chart_global_dates = saved_dates
                st.session_state.multi_securities = saved_securities

            global_input_dates = {}
            colors = ["🔴", "🔵", "🟢", "🟣", "🟡"]
            dates_changed = False
            
            for i in range(5):
                selected_date = st.date_input(
                    f"{colors[i]} 日期 {i+1}", 
                    value=st.session_state.multi_chart_global_dates[i], 
                    key=f"multi_global_date_{i+1}"
                )
                global_input_dates[f'day{i+1}'] = selected_date.strftime('%Y%m%d')
                
                # 检查日期是否发生变化
                if st.session_state.multi_chart_global_dates[i] != selected_date:
                    dates_changed = True
                    st.session_state.multi_chart_global_dates[i] = selected_date

            st.markdown("---")
            st.subheader("证券配置 (最多6个)")

            # 初始化每个图表的配置（已在上面从保存的配置中加载）
            
            # 加载所有已保存的配置用于下拉菜单
            configs = load_user_configs()
            security_configs = {k: v for k, v in configs.items() if k != 'global_settings'}
            config_options = {k: f"{v['security_name']} ({v['symbol']})" for k, v in security_configs.items()}
            options_list = [None] + list(config_options.keys())
            format_func = lambda k: "选择一个配置..." if k is None else config_options[k]
            
            securities_changed = False
            
            for i in range(6):
                with st.expander(f"图表 {i+1}", expanded=(i<3 or st.session_state.multi_securities[i]['symbol'] != '')):
                    
                    # 加载配置的下拉菜单
                    selected_config_key = st.selectbox(
                        "加载已存配置",
                        options=options_list,
                        format_func=format_func,
                        index=options_list.index(st.session_state.multi_securities[i]['config_key']) if st.session_state.multi_securities[i]['config_key'] in options_list else 0,
                        key=f'multi_load_{i}',
                    )

                    # 当用户从下拉菜单选择新配置时，更新状态
                    if selected_config_key != st.session_state.multi_securities[i]['config_key']:
                        securities_changed = True
                        if selected_config_key:
                            config = security_configs[selected_config_key]
                            st.session_state.multi_securities[i].update({
                                'type': config['security_type'],
                                'symbol': config['symbol'],
                                'dates': config['dates'],
                                'use_global_dates': False,
                                'config_key': selected_config_key
                            })
                        else:  # 用户选择 "None"
                            st.session_state.multi_securities[i].update({
                                'use_global_dates': True,
                                'config_key': None
                            })
                        # 立即保存配置
                        save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities)
                        st.rerun()

                    # 证券类型和代码输入
                    sec_type = st.selectbox(
                        f"证券类型", ["股票", "ETF", "指数"],
                        index=["股票", "ETF", "指数"].index(st.session_state.multi_securities[i]['type']),
                        key=f"multi_type_{i}"
                    )
                    symbol = st.text_input(
                        f"证券代码", 
                        value=st.session_state.multi_securities[i]['symbol'], 
                        key=f"multi_symbol_{i}"
                    ).strip()

                    # 是否使用全局日期的复选框
                    use_global = st.checkbox(
                        "使用全局日期",
                        value=st.session_state.multi_securities[i]['use_global_dates'],
                        key=f'multi_global_date_cb_{i}'
                    )
                    
                    # 检查配置是否发生变化并更新状态（来自手动输入）
                    if (st.session_state.multi_securities[i]['type'] != sec_type or 
                        st.session_state.multi_securities[i]['symbol'] != symbol or 
                        st.session_state.multi_securities[i]['use_global_dates'] != use_global):
                        securities_changed = True
                    
                    st.session_state.multi_securities[i]['type'] = sec_type
                    st.session_state.multi_securities[i]['symbol'] = symbol
                    st.session_state.multi_securities[i]['use_global_dates'] = use_global
                    
                    # 如果使用特定日期，则显示提示
                    if not st.session_state.multi_securities[i]['use_global_dates'] and st.session_state.multi_securities[i]['dates']:
                        dates_str = ", ".join([d.replace("2024", "24").replace("2025", "25") for d in st.session_state.multi_securities[i]['dates'].values()])
                        st.info(f"特定日期: {dates_str}", icon="🗓️")


            # 自动保存配置（如果有变化）
            if dates_changed or securities_changed:
                save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities)
                # 只在底部显示一个小的状态指示器，不显示成功消息以避免干扰用户体验

            st.markdown("---")
            
            # 手动保存和重置按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存配置", use_container_width=True):
                    if save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities):
                        st.success("✅ 配置保存成功")
                    else:
                        st.error("❌ 配置保存失败")
            
            with col2:
                if st.button("🔄 重置为默认", use_container_width=True):
                    # 重置为默认配置
                    default_dates, default_securities = load_multi_chart_config.__defaults__[0], load_multi_chart_config.__defaults__[1]
                    # 获取默认配置（重新调用函数但不使用保存的配置）
                    st.session_state.multi_chart_global_dates = [
                        datetime(2024, 9, 24).date(),
                        datetime(2024, 11, 7).date(),
                        datetime(2024, 12, 17).date(),
                        datetime(2025, 4, 7).date(),
                        datetime(2025, 4, 23).date()
                    ]
                    st.session_state.multi_securities = [
                        {'type': '股票', 'symbol': '001215', 'use_global_dates': True, 'dates': None, 'config_key': None},
                        {'type': 'ETF', 'symbol': '159915', 'use_global_dates': True, 'dates': None, 'config_key': None},
                        {'type': '指数', 'symbol': '000001', 'use_global_dates': True, 'dates': None, 'config_key': None},
                        {'type': '股票', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
                        {'type': 'ETF', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
                        {'type': '指数', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
                    ]
                    if save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities):
                        st.success("✅ 已重置为默认配置")
                        st.rerun()
                    else:
                        st.error("❌ 重置失败")

            analyze_button = st.button("🔍 更新看板", type="primary", use_container_width=True)
            
            # 显示最后保存时间
            configs = load_user_configs()
            if 'global_settings' in configs and 'multi_chart_config' in configs['global_settings']:
                save_time = configs['global_settings']['multi_chart_config'].get('save_time', '未知')
                st.caption(f"💾 最后保存: {save_time}")

        st.header("多图概览看板")
        st.info('在左侧配置需要同时监控的证券（最多6个），所有图表将使用相同的KDAS日期。配置完成后，点击"更新看板"以加载图表。')
        st.success('💾 配置自动保存：您的多图看板配置会自动保存，重启或刷新后自动恢复到上次的设置。', icon="✨")
        
        if 'charts_generated' not in st.session_state:
            st.session_state.charts_generated = False

        if analyze_button:
            st.session_state.charts_generated = True

        if st.session_state.charts_generated:
            stock_info_df = load_stock_info()
            etf_info_df = load_etf_info()
            index_info_df = load_index_info()
            info_map = {"股票": stock_info_df, "ETF": etf_info_df, "指数": index_info_df}

            col_defs = [1, 1, 1]
            row1 = st.columns(col_defs)
            row2 = st.columns(col_defs)
            plot_positions = row1 + row2

            for i, pos in enumerate(plot_positions):
                config = st.session_state.multi_securities[i]
                symbol = config['symbol']
                sec_type = config['type']

                with pos:
                    if symbol:
                        try:
                            # 确定当前图表使用的日期
                            if config['use_global_dates']:
                                dates_to_use = global_input_dates
                            elif config['dates']:
                                dates_to_use = config['dates']
                            else: # Fallback
                                dates_to_use = global_input_dates
                                
                            with st.spinner(f"加载 {sec_type} {symbol}..."):
                                info_df = info_map[sec_type]
                                data = get_security_data(symbol, dates_to_use, sec_type)
                                if data.empty:
                                    st.warning(f"无数据: {symbol}")
                                    continue
                                
                                processed_data = calculate_cumulative_vwap(data, dates_to_use)
                                fig = create_mini_chart(processed_data, dates_to_use, info_df, sec_type, symbol)
                                st.plotly_chart(fig, use_container_width=True)

                        except Exception:
                            st.error(f"分析 {symbol} 失败")
                    else:
                        st.markdown(f"<div style='height: 400px; display: flex; align-items: center; justify-content: center; background-color: #f0f2f6; border-radius: 10px; text-align: center; color: grey;'>图表 {i+1}<br>未配置</div>", unsafe_allow_html=True)
        else:
            col_defs = [1, 1, 1]
            row1 = st.columns(col_defs)
            row2 = st.columns(col_defs)
            plot_positions = row1 + row2
            for i, pos in enumerate(plot_positions):
                with pos:
                    st.markdown(f"<div style='height: 400px; display: flex; align-items: center; justify-content: center; background-color: #f0f2f6; border-radius: 10px; text-align: center; color: grey;'>图表 {i+1}<br>等待分析...</div>", unsafe_allow_html=True)


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