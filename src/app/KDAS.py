"""
KDAS证券分析工具 - 主程序文件 (重构版本)

这是一个基于Streamlit的证券技术分析工具，集成了KDAS（累积成交量加权平均价格）指标分析。

重构说明：
- 原有的2800+行代码已模块化拆分为6个专业模块
- 主文件仅保留程序入口和核心业务流程
- 所有功能模块通过导入方式集成

模块架构：
├── config_manager.py    # 配置管理模块
├── data_handler.py      # 数据处理模块  
├── ai_analyzer.py       # AI分析模块
├── chart_generator.py   # 图表生成模块
├── ui_components.py     # UI组件模块
└── KDAS.py             # 主程序入口 (本文件)

技术栈：
- Streamlit: Web界面框架
- 各专业模块: 提供核心功能支持

作者：KDAS团队
版本：2.0 (模块化重构版本)
"""

# === 标准库导入 ===
import os
import sys
from datetime import datetime

# === 第三方库导入 ===
import streamlit as st

# === 模块路径配置 ===
# 确保能够导入本地模块
current_dir = os.path.dirname(__file__)
modules_dir = os.path.join(current_dir, 'modules')
if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)

# === 本地模块导入 ===
try:
    # 配置管理模块
    from modules.config_manager import (
        ConfigManager,
        # 向后兼容的全局函数
        load_user_configs, save_user_configs, get_config_with_validation,
        save_current_config, get_saved_config, delete_saved_config,
        save_api_key, save_ai_analysis_setting, load_ai_analysis_setting,
        save_ai_date_recommendation_setting, load_ai_date_recommendation_setting,
        load_api_key, delete_api_key, save_multi_chart_config, load_multi_chart_config,
        get_default_multi_chart_config, reset_multi_chart_to_default,
        validate_and_cleanup_config, get_config_summary
    )
    
    # 数据处理模块
    from modules.data_handler import (
        DataManager,
        # 向后兼容的全局函数
        load_stock_info, load_etf_info, load_index_info,
        get_security_data, calculate_cumulative_vwap, get_security_name,
        get_trade_calendar, get_non_trading_dates, get_basic_holidays
    )
    
    # AI分析模块
    from modules.ai_analyzer import (
        AIAnalysisManager,
        # 向后兼容的全局函数
        format_analysis_text, get_ai_advisor_instance,
        generate_ai_recommendation, analyze_kdas_state_with_ai
    )
    
    # 图表生成模块
    from modules.chart_generator import (
        ChartGenerator,
        # 向后兼容的全局函数
        create_interactive_chart, create_mini_chart
    )
    
    # UI组件模块
    from modules.ui_components import (
        UIComponentManager,
        # 向后兼容的全局函数
        run_single_chart_analysis_with_kdas, run_multi_chart_analysis_with_kdas,
        render_multi_chart_dashboard, get_multi_chart_summary, render_waiting_dashboard
    )
    
    MODULES_LOADED = True
    print("✅ 所有模块加载成功")
    
except ImportError as e:
    MODULES_LOADED = False
    print(f"❌ 模块导入失败: {e}")
    st.error(f"模块导入失败: {e}")
    st.error("请确保所有模块文件都在 modules/ 目录中")

# === KDAS包导入与初始化 ===
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from kdas import DataHandler, KDASAIAdvisor, KDASAnalyzer, get_ai_advisor, AIRecommendationEngine
    AI_ADVISOR_AVAILABLE = True
    # 初始化全局数据处理器
    data_handler = DataHandler()
    print("✅ KDAS包加载成功")
except ImportError:
    AI_ADVISOR_AVAILABLE = False
    data_handler = None
    print("⚠️ KDAS包未安装，AI功能将不可用")

# === 全局常量和配置 ===
# 数据目录路径（相对于项目根目录）
data_root = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
os.makedirs(os.path.join(data_root, 'shares'), exist_ok=True)
os.makedirs(os.path.join(data_root, 'etfs'), exist_ok=True)
os.makedirs(os.path.join(data_root, 'stocks'), exist_ok=True)

def main():
    """主程序入口函数"""
    if not MODULES_LOADED:
        st.error("❌ 模块加载失败，无法启动应用")
        st.stop()
    
    st.set_page_config(page_title="KDAS证券分析工具", layout="wide")
    
    # 应用启动时验证和清理配置文件
    if 'config_validated' not in st.session_state:
        try:
            validate_and_cleanup_config()
            st.session_state.config_validated = True
        except Exception as e:
            st.warning(f"配置文件验证时出现问题: {e}")
    
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
        render_single_chart_mode()
    else:  # 多图概览看板
        render_multi_chart_mode()

def render_single_chart_mode():
    """渲染单图精细分析模式"""
    # 检查是否需要加载完整配置
    load_full_config = st.session_state.get('load_full_config', None)
    if load_full_config:
        st.success(f"✅ 已加载完整配置: {load_full_config['symbol']}")
        # 将配置信息设置到session_state中，用于组件显示
        st.session_state.current_security_type = load_full_config['security_type']
        st.session_state.current_symbol = load_full_config['symbol']
        st.session_state.current_dates = load_full_config['dates']
        # 重置日期初始化标志，确保新配置能够应用
        st.session_state.dates_initialized = False
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
            render_ai_config_section()
        
        # 日期选择器
        input_date = render_date_selection_section(saved_config)
        
        # 分析按钮
        analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)
        
        # 清除配置按钮
        render_config_management_section()
    
    # 主要内容区域
    render_single_chart_analysis(security_type, symbol, input_date, analyze_button, info_df)

def render_ai_config_section():
    """渲染AI配置区域"""
    st.markdown("#### 🤖 AI智能推荐")
    
    # 加载保存的API密钥和模型配置
    saved_api_key, saved_model = load_api_key()
    
    # AI日期推荐开关
    ai_date_recommendation_enabled = load_ai_date_recommendation_setting()
    ai_date_enabled_checkbox = st.checkbox(
        "📅 启用AI日期推荐", 
        value=ai_date_recommendation_enabled,
        help="开启后分析时将自动使用AI推荐的最佳关键日期"
    )
    
    # 保存AI日期推荐开关设置
    if ai_date_enabled_checkbox != ai_date_recommendation_enabled:
        save_ai_date_recommendation_setting(ai_date_enabled_checkbox)
    
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
    
    # 根据AI选项组合显示相应提示
    if not ai_date_enabled_checkbox and not ai_enabled_checkbox:
        st.info("💡 可勾选上方AI选项以启用智能功能：日期推荐 + 状态分析")
    elif ai_date_enabled_checkbox and not ai_enabled_checkbox:
        st.info("💡 当前将使用AI推荐日期，可额外勾选「🔮 启用AI智能分析」获得分析报告")
    elif not ai_date_enabled_checkbox and ai_enabled_checkbox:
        st.info("💡 当前将分析手动选择的日期，可额外勾选「📅 启用AI日期推荐」自动推荐最佳日期")
    else:
        # 两个AI功能都启用时的提示
        if not saved_api_key:
            st.warning("⚠️ 已启用AI功能，但需要配置API密钥才能使用")
        else:
            st.success("✅ AI完整功能已启用：智能日期推荐 + 状态分析")
    
    # API密钥输入
    api_key_input = st.text_input(
        "AI API密钥", 
        value=saved_api_key,
        type="password", 
        help="输入您的AI API密钥以使用AI功能（日期推荐和智能分析）",
        placeholder="sk-..."
    )
    
    # 模型选择
    model_options = ["deepseek-r1", "gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-03-25"]
    default_model_index = 0
    if saved_model in model_options:
        default_model_index = model_options.index(saved_model)
    
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
                st.rerun()
            else:
                st.error("❌ 清除失败，请重试")
    
    if api_key_input:
        os.environ['OPENAI_API_KEY'] = api_key_input

    st.markdown("---")

def render_date_selection_section(saved_config):
    """渲染日期选择区域"""
    # 使用日期选择器
    default_dates = [
        datetime(2024, 9, 24).date(),
        datetime(2024, 11, 7).date(),
        datetime(2024, 12, 17).date(),
        datetime(2025, 4, 7).date(),
        datetime(2025, 4, 23).date()
    ]
    
    # 初始化日期状态（只在第一次或明确需要时设置）
    dates_initialized = st.session_state.get('dates_initialized', False)
    
    # 如果有当前配置且尚未初始化，使用配置中的日期
    if (st.session_state.get('current_dates') and not dates_initialized):
        current_dates = st.session_state.current_dates
        try:
            for i, (key, date_str) in enumerate(current_dates.items()):
                if i < len(default_dates):
                    date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                    st.session_state[f"date_{i+1}"] = date_obj
            st.session_state.dates_initialized = True
        except Exception as e:
            st.warning(f"加载完整配置的日期失败: {e}")
    
    # 如果有保存的配置且用户选择加载，则使用保存的日期
    elif (saved_config and 
        hasattr(st.session_state, 'load_saved_config') and 
        st.session_state.load_saved_config):
        try:
            for i, (key, date_str) in enumerate(saved_config['dates'].items()):
                date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                st.session_state[f"date_{i+1}"] = date_obj
            st.session_state.load_saved_config = False
            st.session_state.dates_initialized = True
            st.success("✅ 已加载保存的日期配置！")
        except Exception as e:
            st.warning(f"加载保存的日期配置失败: {e}")
    
    # 初始化默认日期（只在第一次时）
    elif not dates_initialized:
        for i in range(5):
            date_key = f"date_{i+1}"
            if date_key not in st.session_state:
                st.session_state[date_key] = default_dates[i]
        st.session_state.dates_initialized = True
    
    input_date = {}
    colors = ["🔴", "🔵", "🟢", "🟣", "🟡"]
    
    for i in range(5):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.write(f"{colors[i]} Day{i+1}")
        with col2:
            date_key = f"date_{i+1}"
            # 确保日期键存在（防御性编程）
            if date_key not in st.session_state:
                st.session_state[date_key] = default_dates[i]
            
            selected_date = st.date_input(
                f"日期{i+1}",
                key=f"date_{i+1}"
            )
            
            input_date[f'day{i+1}'] = selected_date.strftime('%Y%m%d')
    
    return input_date

def render_config_management_section():
    """渲染配置管理区域"""
    # 如果当前有加载的配置或分析状态，显示清除按钮
    has_current_config = (st.session_state.get('current_security_type') or 
                        st.session_state.get('current_symbol') or 
                        st.session_state.get('current_dates'))
    has_analysis_state = st.session_state.get('current_analysis')
    
    if has_current_config or has_analysis_state:
        if st.button("🔄 清除当前配置", use_container_width=True):
            # 清除当前配置
            keys_to_clear = [
                'current_security_type', 'current_symbol', 'current_dates', 'current_analysis', 'dates_initialized'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 清除所有分析状态
            analysis_keys = [k for k in st.session_state.keys() if k.startswith('analysis_')]
            for key in analysis_keys:
                del st.session_state[key]
            
            # 同时清除日期选择器的session_state值
            for i in range(5):
                date_key = f"date_{i+1}"
                if date_key in st.session_state:
                    del st.session_state[date_key]
                    
            st.rerun()
    
    # 配置管理
    st.markdown("---")
    st.subheader("💾 配置管理")
    
    # 显示已保存的配置
    configs = load_user_configs()
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
                        keys_to_clear = ['current_security_type', 'current_symbol', 'current_dates', 'load_saved_config', 'dates_initialized']
                        for key in keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        # 清除日期选择器的session_state值
                        for i in range(5):
                            date_key = f"date_{i+1}"
                            if date_key in st.session_state:
                                del st.session_state[date_key]
                        
                        # 设置加载标志
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

def render_single_chart_analysis(security_type, symbol, input_date, analyze_button, info_df):
    """渲染单图分析主要内容"""
    # 检查是否有保存的分析状态
    current_analysis_key = f"analysis_{security_type}_{symbol}"
    has_saved_analysis = (current_analysis_key in st.session_state and 
                         st.session_state.get('current_analysis') == current_analysis_key)
    
    if analyze_button or has_saved_analysis:
        # 预检查：验证输入参数
        if not symbol or len(symbol.strip()) != 6:
            st.error("❌ 请输入正确的6位证券代码")
            st.stop()
        
        # 检查AI功能配置
        saved_api_key, saved_model = load_api_key()
        ai_date_recommendation_enabled = load_ai_date_recommendation_setting()
        ai_analysis_enabled = load_ai_analysis_setting()
        
        # 如果启用了AI功能但没有API密钥，给出提示
        if (ai_date_recommendation_enabled or ai_analysis_enabled) and not saved_api_key:
            st.warning("⚠️ 您已启用AI功能，但未配置API密钥。将使用手动模式进行分析。")
            st.info("💡 如需使用AI功能，请在左侧边栏配置API密钥")
        
        try:
            # 如果点击了分析按钮，强制重新分析
            if analyze_button:
                st.session_state['force_reanalyze'] = True
                # 清除可能存在的旧分析状态（如果用户更换了证券）
                old_keys = [k for k in st.session_state.keys() if k.startswith('analysis_state_')]
                for old_key in old_keys:
                    if old_key != f"analysis_state_{security_type}_{symbol}":
                        del st.session_state[old_key]
            
            # 按照期望的流程进行分析
            render_step_by_step_analysis(security_type, symbol, input_date, saved_api_key, saved_model, 
                                       ai_date_recommendation_enabled, ai_analysis_enabled, info_df)
            
        except Exception as e:
            st.error(f"分析过程中出现错误: {str(e)}")
            st.info("请检查股票代码是否正确，或稍后重试。")
    
    else:
        # 显示使用说明
        render_usage_instructions()

def render_step_by_step_analysis(security_type, symbol, input_date, saved_api_key, saved_model, 
                                ai_date_recommendation_enabled, ai_analysis_enabled, info_df):
    """按步骤渲染分析流程：1.AI日期推荐 -> 2.展示图表 -> 3.AI分析 -> 4.展示结果"""
    
    # 创建唯一的分析状态键
    analysis_state_key = f"analysis_state_{security_type}_{symbol}"
    
    # 检查是否需要重新分析（如果按钮被点击且还没有分析状态，或者配置发生了变化）
    should_analyze = (analysis_state_key not in st.session_state or 
                      st.session_state.get('force_reanalyze', False))
    
    if should_analyze:
        # 清除强制重分析标志
        if 'force_reanalyze' in st.session_state:
            del st.session_state['force_reanalyze']
        
        # 获取证券名称
        security_name = get_security_name(symbol, security_type)
        
        # === 步骤1: AI日期推荐 ===
        final_dates = input_date  # 默认使用手动日期
        recommendation_result = None
        
        if ai_date_recommendation_enabled and saved_api_key and AI_ADVISOR_AVAILABLE:
            st.subheader("🤖 步骤1: AI智能日期推荐")
            
            with st.spinner("🔄 AI正在分析最佳关键日期..."):
                try:
                    # 调用AI日期推荐
                    recommendation_result = generate_ai_recommendation(
                        symbol, security_type, saved_api_key, saved_model
                    )
                    
                    if recommendation_result and recommendation_result.get('success', False):
                        st.success("✅ AI日期推荐完成")
                        
                        # 显示推荐结果
                        recommended_dates = recommendation_result.get('recommended_dates', [])
                        if recommended_dates:
                            # 转换推荐日期为字典格式
                            final_dates = {}
                            for i, date_str in enumerate(recommended_dates[:5]):
                                final_dates[f'day{i+1}'] = date_str
                    else:
                        st.warning("⚠️ AI日期推荐失败，将使用手动设置的日期")
                        if recommendation_result:
                            st.error(f"错误信息: {recommendation_result.get('error', '未知错误')}")
                            
                except Exception as e:
                    st.warning(f"⚠️ AI日期推荐出现异常: {str(e)}，将使用手动设置的日期")
            
            st.markdown("---")
        
        # === 步骤2: 获取数据并展示图表 ===
        st.subheader("📊 步骤2: 数据分析与图表展示")
        
        with st.spinner("📈 正在获取数据并计算KDAS指标..."):
            # 获取证券数据
            df = get_security_data(symbol, final_dates, security_type)
            if df.empty:
                st.error(f"❌ 未找到该{security_type}的数据，请检查{security_type}代码是否正确。")
                return
            
            # 计算KDAS
            processed_data = calculate_cumulative_vwap(df, final_dates)
        
        st.markdown("---")
        
        # === 步骤3: AI状态分析 ===
        ai_analysis_result = None
        
        if ai_analysis_enabled and saved_api_key and AI_ADVISOR_AVAILABLE:
            st.subheader("🔮 步骤3: AI智能状态分析")
            
            with st.spinner("🤖 AI正在分析KDAS状态..."):
                try:
                    # 调用AI状态分析
                    ai_analysis_result = analyze_kdas_state_with_ai(
                        processed_data, final_dates, symbol, security_type, saved_api_key, saved_model
                    )
                    
                    if ai_analysis_result and ai_analysis_result.get('success', False):
                        st.success("✅ AI状态分析完成")
                    else:
                        st.warning("⚠️ AI状态分析失败")
                        if ai_analysis_result:
                            st.error(f"错误信息: {ai_analysis_result.get('error', '未知错误')}")
                            
                except Exception as e:
                    st.warning(f"⚠️ AI状态分析出现异常: {str(e)}")
            
            st.markdown("---")
        
        # 保存分析状态到session_state
        st.session_state[analysis_state_key] = {
            'security_name': security_name,
            'df': df,
            'processed_data': processed_data,
            'final_dates': final_dates,
            'recommendation_result': recommendation_result,
            'ai_analysis_result': ai_analysis_result,
            'ai_date_recommendation_enabled': ai_date_recommendation_enabled,
            'ai_analysis_enabled': ai_analysis_enabled,
            'latest_price': processed_data['收盘'].iloc[-1],
            'price_change': processed_data['收盘'].iloc[-1] - processed_data['收盘'].iloc[-2] if len(processed_data) > 1 else 0
        }
    
    # 从session_state加载分析状态
    analysis_state = st.session_state.get(analysis_state_key)
    if not analysis_state:
        st.error("❌ 分析状态丢失，请重新分析")
        return
    
    # 提取保存的数据
    security_name = analysis_state['security_name']
    df = analysis_state['df']
    processed_data = analysis_state['processed_data']
    final_dates = analysis_state['final_dates']
    recommendation_result = analysis_state['recommendation_result']
    ai_analysis_result = analysis_state['ai_analysis_result']
    ai_date_recommendation_enabled = analysis_state['ai_date_recommendation_enabled']
    ai_analysis_enabled = analysis_state['ai_analysis_enabled']
    
    # === 显示步骤1结果: AI日期推荐 ===
    if ai_date_recommendation_enabled and recommendation_result and recommendation_result.get('success', False):
        st.subheader("🤖 步骤1: AI智能日期推荐")
        st.success("✅ AI日期推荐完成")
        
        # 显示推荐结果
        recommended_dates = recommendation_result.get('recommended_dates', [])
        if recommended_dates:
            st.info("📅 **AI推荐的关键日期：**")
            cols = st.columns(5)
            colors = ["🔴", "🔵", "🟢", "🟣", "🟡"]
            
            for i, date_str in enumerate(recommended_dates[:5]):
                with cols[i]:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                        st.metric(f"{colors[i]} Day{i+1}", date_obj.strftime('%m-%d'))
                    except:
                        st.metric(f"{colors[i]} Day{i+1}", date_str)
        
        # 显示推荐理由
        recommendation_text = recommendation_result.get('recommendation', '')
        if recommendation_text:
            with st.expander("💡 查看推荐理由", expanded=False):
                formatted_recommendation = format_analysis_text(recommendation_text)
                st.markdown(formatted_recommendation, unsafe_allow_html=True)
        
        st.markdown("---")
    
    # === 显示步骤2结果: 数据分析与图表展示 ===
    st.subheader("📊 步骤2: 数据分析与图表展示")
    
    # 显示基本信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(f"{security_type}名称", security_name)
    with col2:
        st.metric(f"{security_type}代码", symbol)
    with col3:
        latest_price = analysis_state['latest_price']
        st.metric("最新收盘价", f"¥{latest_price:.3f}")
    with col4:
        price_change = analysis_state['price_change']
        if price_change != 0:
            st.metric("涨跌", f"¥{price_change:.3f}", delta=f"{(price_change/latest_price*100):.3f}%")
        else:
            st.metric("涨跌", "暂无数据")
    
    # 创建并显示图表
    fig = create_interactive_chart(processed_data, final_dates, info_df, security_type, symbol)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # === 显示步骤3结果: AI状态分析 ===
    if ai_analysis_enabled:
        st.subheader("🔮 步骤3: AI智能状态分析")
        if ai_analysis_result and ai_analysis_result.get('success', False):
            st.success("✅ AI状态分析完成")
        else:
            st.warning("⚠️ AI状态分析失败或未启用")
        st.markdown("---")
    
    # === 显示步骤4结果: 分析结果展示 ===
    st.subheader("📈 步骤4: 分析结果展示")
    
    # 显示AI分析结果
    if ai_analysis_result and ai_analysis_result.get('success', False):
        analysis_text = ai_analysis_result.get('analysis', '')
        if analysis_text:
            formatted_analysis = format_analysis_text(analysis_text)
            with st.expander("📊 查看详细KDAS状态分析报告", expanded=True):
                st.markdown(formatted_analysis, unsafe_allow_html=True)
    else:
        # 显示AI配置提示
        if not ai_analysis_enabled:
            st.info("💡 **启用KDAS智能分析**")
            st.markdown("勾选左侧边栏「🔮 启用AI智能分析」选项，此处将自动显示专业的KDAS状态分析报告")
        elif not saved_api_key:
            st.info("💡 **配置AI API密钥**")
            st.markdown("您已启用AI智能分析，但还需要配置API密钥才能使用")
            st.warning("⚠️ 需要先在左侧边栏的AI智能推荐区域配置API密钥")
        elif not AI_ADVISOR_AVAILABLE:
            st.warning("⚠️ AI功能不可用，请检查kdas包是否正确安装")
    
    # 保存配置逻辑
    st.markdown("---")
    if ai_date_recommendation_enabled and recommendation_result and recommendation_result.get('success', False):
        # 使用AI推荐日期时的手动保存选项
        col_save1, col_save2 = st.columns(2)
        with col_save1:
            st.info("💡 当前使用AI推荐日期")
        with col_save2:
            # 使用不同的key避免重复
            save_button_key = f"save_ai_config_{security_type}_{symbol}"
            if st.button("💾 保存AI推荐配置", key=save_button_key, help="将当前的AI推荐日期保存为配置"):
                save_success, save_message = save_current_config(symbol, security_type, final_dates, security_name)
                if save_success:
                    st.success("✅ AI推荐配置已保存！")
                else:
                    st.error(f"❌ 保存失败: {save_message}")
    else:
        # 手动日期模式的自动保存
        save_success, save_message = save_current_config(symbol, security_type, final_dates, security_name)
        if save_success:
            st.success("✅ 当前配置已自动保存，下次可直接加载！")
        else:
            st.warning(f"⚠️ 配置自动保存失败: {save_message}")

def render_analysis_results(analysis_result, info_df, security_type, symbol, input_date):
    """渲染分析结果"""
    data = analysis_result['data']
    processed_data = analysis_result['processed_data']
    security_name = analysis_result['security_name']
    analysis_dates = analysis_result['input_dates']
    
    # 显示基本信息
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
    
    # 显示图表和AI分析
    col_chart, col_analysis = st.columns([3, 2])
    
    with col_chart:
        # 创建并显示图表
        fig = create_interactive_chart(processed_data, analysis_dates, info_df, security_type, symbol)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_analysis:
        st.subheader("🤖 KDAS智能分析")
        
        ai_analysis_result = analysis_result.get('ai_analysis_result')
        if ai_analysis_result and ai_analysis_result.get('success', False):
            st.success("✅ AI状态分析完成")
            
            # 格式化分析结果
            analysis_text = ai_analysis_result.get('analysis', '')
            if analysis_text:
                formatted_analysis = format_analysis_text(analysis_text)
                with st.expander("📈 查看详细分析报告", expanded=True):
                    st.markdown(formatted_analysis, unsafe_allow_html=True)
        else:
            # 显示AI配置提示
            ai_analysis_enabled = load_ai_analysis_setting()
            saved_api_key, _ = load_api_key()
            
            if not ai_analysis_enabled:
                st.info("💡 **启用KDAS智能分析**")
                st.markdown("勾选左侧边栏「🔮 启用AI智能分析」选项，此处将自动显示专业的KDAS状态分析报告")
            elif not saved_api_key:
                st.info("💡 **配置AI API密钥**")
                st.markdown("您已启用AI智能分析，但还需要配置API密钥才能使用")
                st.warning("⚠️ 需要先在左侧边栏的AI智能推荐区域配置API密钥")
            elif not AI_ADVISOR_AVAILABLE:
                st.warning("⚠️ AI功能不可用，请检查kdas包是否正确安装")
    
    # 保存配置逻辑
    st.markdown("---")
    mode = analysis_result.get('mode', 'manual')
    if mode == 'ai_integrated':
        # 使用AI推荐日期时的手动保存选项
        col_save1, col_save2 = st.columns(2)
        with col_save1:
            st.info("💡 当前使用AI推荐日期")
        with col_save2:
            if st.button("💾 保存AI推荐配置", help="将当前的AI推荐日期保存为配置"):
                save_success, save_message = save_current_config(symbol, security_type, analysis_dates, security_name)
                if save_success:
                    st.success("✅ AI推荐配置已保存！")
                else:
                    st.error(f"❌ 保存失败: {save_message}")
    else:
        # 手动日期模式的自动保存
        save_success, save_message = save_current_config(symbol, security_type, analysis_dates, security_name)
        if save_success:
            st.success("✅ 当前配置已自动保存，下次可直接加载！")
        else:
            st.warning(f"⚠️ 配置自动保存失败: {save_message}")

def render_multi_chart_mode():
    """渲染多图概览看板模式"""
    with st.sidebar:
        st.header("📊 多图看板配置")
        st.subheader("全局KDAS计算起始日期")

        # 定义全局日期和证券配置 - 从保存的配置中加载
        if 'multi_chart_global_dates' not in st.session_state or 'multi_securities' not in st.session_state:
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
            
            if st.session_state.multi_chart_global_dates[i] != selected_date:
                dates_changed = True
                st.session_state.multi_chart_global_dates[i] = selected_date

        st.markdown("---")
        st.subheader("证券配置 (最多6个)")

        # 配置证券列表
        render_multi_chart_securities_config(dates_changed)
        
        # 分析按钮
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
        # 使用UI组件模块的多图分析函数
        with st.spinner("🔄 正在生成多图看板..."):
            analysis_results = run_multi_chart_analysis_with_kdas(
                st.session_state.multi_securities, 
                global_input_dates
            )
        
        # 显示分析汇总
        summary = get_multi_chart_summary(analysis_results)
        
        # 创建状态指示器
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("成功图表", summary['successful_charts'], f"共 {summary['total_charts']} 个")
        with col_info2:
            success_rate_pct = summary['success_rate'] * 100
            st.metric("成功率", f"{success_rate_pct:.1f}%")
        with col_info3:
            if summary['type_statistics']:
                type_info = ", ".join([f"{k}:{v}" for k, v in summary['type_statistics'].items()])
                st.metric("证券类型", type_info)
            else:
                st.metric("证券类型", "无数据")
        
        # 显示失败的证券（如果有）
        if summary['failed_securities']:
            with st.expander(f"⚠️ 失败的证券 ({len(summary['failed_securities'])}个)", expanded=False):
                for failed_sec in summary['failed_securities']:
                    st.warning(failed_sec)
        
        st.markdown("---")
        
        # 渲染图表看板
        render_multi_chart_dashboard(analysis_results)
    else:
        # 显示等待状态的看板
        render_waiting_dashboard()

def render_multi_chart_securities_config(dates_changed):
    """渲染多图看板证券配置区域"""
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
                else:
                    st.session_state.multi_securities[i].update({
                        'use_global_dates': True,
                        'config_key': None
                    })
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
            
            # 检查配置是否发生变化并更新状态
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
            default_dates, default_securities = get_default_multi_chart_config()
            st.session_state.multi_chart_global_dates = default_dates
            st.session_state.multi_securities = default_securities
            if save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities):
                st.success("✅ 已重置为默认配置")
                st.rerun()
            else:
                st.error("❌ 重置失败")

def render_usage_instructions():
    """渲染使用说明"""
    st.info("👈 请在左侧边栏配置参数并点击「开始分析」按钮")
    
    with st.expander("📖 使用说明"):
        st.markdown("""
        ### KDAS指标说明
        KDAS（Key Date Average Settlement）是基于关键日期的累计成交量加权平均价格指标。作者： 叙市 （全网同名）
        
        ### 使用步骤
        1. 选择证券类型（股票、ETF、指数）
        2. 输入对应的6位证券代码
        3. **(可选)** 配置AI功能
        4. 手动选择5个关键的分析日期（如未启用AI日期推荐）
        5. 点击「开始分析」按钮
        6. 查看K线图、KDAS指标走势和AI分析报告
        
        ### 🤖 AI智能功能
        - **📅 智能日期推荐**: 基于AI分析推荐最佳关键日期
        - **📊 KDAS状态智能分析**: 实时分析当前市场状态
        - **🔧 配置管理**: 支持API密钥保存和多模型选择
        
        ### 💾 记忆功能
        - **自动保存**: 每次分析后自动保存配置
        - **智能识别**: 自动提示已保存的配置
        - **配置管理**: 可查看和删除已保存的配置
        """)

if __name__ == "__main__":
    # 检测是否通过streamlit运行
    try:
        import streamlit.runtime.scriptrunner.script_run_context as ctx
        if ctx.get_script_run_ctx() is None:
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