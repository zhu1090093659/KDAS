"""
KDAS证券分析工具 - UI组件模块

该模块负责处理所有用户界面相关的功能，包括：
- 单图精细分析的业务逻辑
- 多图看板的分析和渲染
- UI组件的渲染和交互处理
- 分析结果的汇总和展示

主要功能：
1. run_single_chart_analysis_with_kdas: 单图精细分析的完整业务逻辑
2. run_multi_chart_analysis_with_kdas: 多图看板分析功能
3. render_multi_chart_dashboard: 多图看板的结果展示
4. get_multi_chart_summary: 分析结果汇总
5. render_waiting_dashboard: 等待状态的看板渲染

技术栈：
- streamlit: Web界面框架
- asyncio: 异步处理
- pandas: 数据处理

作者：KDAS团队
版本：2.0 (模块化重构版本)
"""

# === 标准库导入 ===
import asyncio
from datetime import datetime
import os

# === 第三方库导入 ===
import streamlit as st

# === 本地模块导入 ===
try:
    from .data_handler import (
        get_security_data, calculate_cumulative_vwap, get_security_name,
        load_stock_info, load_etf_info, load_index_info
    )
    from .ai_analyzer import (
        get_ai_advisor_instance, analyze_kdas_state_with_ai
    )
    from .chart_generator import create_mini_chart
    from .config_manager import load_ai_analysis_setting
except ImportError:
    # 备用导入方案
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from data_handler import (
        get_security_data, calculate_cumulative_vwap, get_security_name,
        load_stock_info, load_etf_info, load_index_info
    )
    from ai_analyzer import (
        get_ai_advisor_instance, analyze_kdas_state_with_ai
    )
    from chart_generator import create_mini_chart
    from config_manager import load_ai_analysis_setting

# === 全局变量 ===
try:
    # 尝试导入kdas包的可用性标志
    from ..KDAS import AI_ADVISOR_AVAILABLE
except ImportError:
    # 备用方案
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from kdas import DataHandler, KDASAIAdvisor, KDASAnalyzer, get_ai_advisor, AIRecommendationEngine
        AI_ADVISOR_AVAILABLE = True
    except ImportError:
        AI_ADVISOR_AVAILABLE = False


class UIComponentManager:
    """UI组件管理器类，负责处理所有UI相关的业务逻辑"""
    
    def __init__(self):
        """初始化UI组件管理器"""
        self.ai_advisor_available = AI_ADVISOR_AVAILABLE
    
    def run_single_chart_analysis_with_kdas(self, security_type, symbol, api_key=None, model="deepseek-r1", manual_dates=None):
        """
        使用kdas包的集成功能进行单图精细分析
        
        Args:
            security_type: 证券类型
            symbol: 证券代码
            api_key: AI API密钥
            model: AI模型名称
            manual_dates: 手动指定的日期字典，如果提供则不使用AI推荐
        
        Returns:
            分析结果字典
        """
        try:
            # 1. 获取证券名称
            security_name = get_security_name(symbol, security_type)
            
            # 2. 判断是使用AI推荐还是手动日期
            if manual_dates and not any(st.session_state.get('using_ai_dates', False) for _ in [True]):
                # 使用手动日期
                input_date = manual_dates
                df = get_security_data(symbol, input_date, security_type)
                if df.empty:
                    return {
                        'success': False,
                        'error': f'未找到该{security_type}的数据，请检查{security_type}代码是否正确。',
                        'data': None,
                        'processed_data': None,
                        'security_name': security_name,
                        'recommendation_result': None,
                        'ai_analysis_result': None
                    }
                
                # 计算KDAS
                processed_data = calculate_cumulative_vwap(df, input_date)
                
                # 如果有API密钥，进行AI状态分析
                ai_analysis_result = None
                if api_key and load_ai_analysis_setting():
                    ai_analysis_result = analyze_kdas_state_with_ai(
                        processed_data, input_date, symbol, security_type, api_key, model
                    )
                
                return {
                    'success': True,
                    'data': df,
                    'processed_data': processed_data,
                    'security_name': security_name,
                    'input_dates': input_date,
                    'recommendation_result': None,
                    'ai_analysis_result': ai_analysis_result,
                    'mode': 'manual'
                }
            
            elif api_key and self.ai_advisor_available:
                # 使用kdas包的完整集成分析
                try:
                    # 使用kdas包的集成功能
                    advisor = get_ai_advisor_instance(api_key, model)
                    if advisor is None:
                        raise Exception("无法创建AI顾问实例")
                    
                    # 异步调用需要在同步函数中处理
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        kdas_result = loop.run_until_complete(
                            advisor.analyze_all_async(security_type, symbol, api_key, model)
                        )
                    finally:
                        loop.close()
                    
                    if not kdas_result.get('success', False):
                        # 如果AI分析失败，回退到手动模式
                        if manual_dates:
                            return self.run_single_chart_analysis_with_kdas(
                                security_type, symbol, api_key, model, manual_dates
                            )
                        else:
                            return {
                                'success': False,
                                'error': f'AI分析失败: {kdas_result.get("error", "未知错误")}',
                                'data': None,
                                'processed_data': None,
                                'security_name': security_name,
                                'recommendation_result': kdas_result.get('recommendation'),
                                'ai_analysis_result': kdas_result.get('analysis')
                            }
                    
                    # 成功获得AI推荐，使用推荐的日期重新获取数据和计算KDAS
                    recommended_dates_dict = kdas_result.get('input_dates', {})
                    df = get_security_data(symbol, recommended_dates_dict, security_type)
                    processed_data = calculate_cumulative_vwap(df, recommended_dates_dict)
                    
                    return {
                        'success': True,
                        'data': df,
                        'processed_data': processed_data,
                        'security_name': security_name,
                        'input_dates': recommended_dates_dict,
                        'recommendation_result': kdas_result.get('recommendation'),
                        'ai_analysis_result': kdas_result.get('analysis'),
                        'mode': 'ai_integrated',
                        'recommended_dates': kdas_result.get('recommended_dates', [])
                    }
                    
                except Exception as e:
                    # AI分析出错，如果有手动日期则回退
                    if manual_dates:
                        return self.run_single_chart_analysis_with_kdas(
                            security_type, symbol, api_key, model, manual_dates
                        )
                    else:
                        return {
                            'success': False,
                            'error': f'AI集成分析失败: {str(e)}',
                            'data': None,
                            'processed_data': None,
                            'security_name': security_name,
                            'recommendation_result': None,
                            'ai_analysis_result': None
                        }
            
            else:
                # 没有API密钥或AI不可用，必须使用手动日期
                if not manual_dates:
                    return {
                        'success': False,
                        'error': '没有配置AI API密钥，请手动选择日期或配置API密钥',
                        'data': None,
                        'processed_data': None,
                        'security_name': security_name,
                        'recommendation_result': None,
                        'ai_analysis_result': None
                    }
                
                return self.run_single_chart_analysis_with_kdas(
                    security_type, symbol, api_key, model, manual_dates
                )
        
        except Exception as e:
            return {
                'success': False,
                'error': f'分析过程中出现错误: {str(e)}',
                'data': None,
                'processed_data': None,
                'security_name': get_security_name(symbol, security_type) if symbol else "未知",
                'recommendation_result': None,
                'ai_analysis_result': None
            }
    
    def run_multi_chart_analysis_with_kdas(self, securities_config, global_dates):
        """
        使用kdas包优化多图看板分析功能
        
        Args:
            securities_config: 证券配置列表
            global_dates: 全局日期配置
        
        Returns:
            分析结果列表
        """
        results = []
        
        # 预加载数据源映射
        info_sources = {
            "股票": load_stock_info(),
            "ETF": load_etf_info(), 
            "指数": load_index_info()
        }
        
        for i, config in enumerate(securities_config):
            symbol = config.get('symbol', '').strip()
            sec_type = config.get('type', '股票')
            
            # 跳过空的配置
            if not symbol:
                results.append({
                    'success': False,
                    'index': i,
                    'symbol': '',
                    'type': sec_type,
                    'error': '未配置证券代码',
                    'data': None,
                    'processed_data': None,
                    'fig': None
                })
                continue
            
            try:
                # 确定使用的日期
                if config.get('use_global_dates', True):
                    dates_to_use = global_dates
                elif config.get('dates'):
                    dates_to_use = config['dates']
                else:
                    dates_to_use = global_dates
                
                # 使用已优化的数据获取函数
                data = get_security_data(symbol, dates_to_use, sec_type)
                
                if data.empty:
                    results.append({
                        'success': False,
                        'index': i,
                        'symbol': symbol,
                        'type': sec_type,
                        'error': f'未找到{sec_type}数据',
                        'data': None,
                        'processed_data': None,
                        'fig': None
                    })
                    continue
                
                # 计算KDAS
                processed_data = calculate_cumulative_vwap(data, dates_to_use)
                
                # 创建图表
                info_df = info_sources[sec_type]
                fig = create_mini_chart(processed_data, dates_to_use, info_df, sec_type, symbol)
                
                results.append({
                    'success': True,
                    'index': i,
                    'symbol': symbol,
                    'type': sec_type,
                    'data': data,
                    'processed_data': processed_data,
                    'fig': fig,
                    'dates_used': dates_to_use
                })
                
            except Exception as e:
                results.append({
                    'success': False,
                    'index': i,
                    'symbol': symbol,
                    'type': sec_type,
                    'error': str(e),
                    'data': None,
                    'processed_data': None,
                    'fig': None
                })
        
        return results
    
    def render_multi_chart_dashboard(self, analysis_results):
        """
        渲染多图看板的结果展示
        
        Args:
            analysis_results: 分析结果列表
        """
        # 创建3x2的网格布局
        col_defs = [1, 1, 1]
        row1 = st.columns(col_defs)
        row2 = st.columns(col_defs)
        plot_positions = row1 + row2
        
        for i, pos in enumerate(plot_positions):
            with pos:
                if i < len(analysis_results):
                    result = analysis_results[i]
                    
                    if result['success']:
                        # 显示成功的图表
                        st.plotly_chart(result['fig'], use_container_width=True)
                    else:
                        # 显示错误信息
                        if result['symbol']:
                            error_msg = f"图表 {i+1}: {result['symbol']}<br>❌ {result['error']}"
                        else:
                            error_msg = f"图表 {i+1}<br>未配置"
                        
                        st.markdown(
                            f"<div style='height: 400px; display: flex; align-items: center; "
                            f"justify-content: center; background-color: #ffebee; border: 1px solid #f44336; "
                            f"border-radius: 10px; text-align: center; color: #d32f2f;'>{error_msg}</div>", 
                            unsafe_allow_html=True
                        )
                else:
                    # 显示空白占位符
                    st.markdown(
                        f"<div style='height: 400px; display: flex; align-items: center; "
                        f"justify-content: center; background-color: #f0f2f6; border-radius: 10px; "
                        f"text-align: center; color: grey;'>图表 {i+1}<br>未配置</div>", 
                        unsafe_allow_html=True
                    )
    
    def get_multi_chart_summary(self, analysis_results):
        """
        获取多图看板分析的汇总信息
        
        Args:
            analysis_results: 分析结果列表
        
        Returns:
            汇总信息字典
        """
        total_charts = len(analysis_results)
        successful_charts = sum(1 for r in analysis_results if r['success'])
        failed_charts = total_charts - successful_charts
        
        # 按类型统计
        type_stats = {}
        for result in analysis_results:
            if result['success']:
                sec_type = result['type']
                type_stats[sec_type] = type_stats.get(sec_type, 0) + 1
        
        # 获取失败的证券列表
        failed_securities = [
            f"{r['symbol']} ({r['type']})" 
            for r in analysis_results 
            if not r['success'] and r['symbol']
        ]
        
        return {
            'total_charts': total_charts,
            'successful_charts': successful_charts,
            'failed_charts': failed_charts,
            'type_statistics': type_stats,
            'failed_securities': failed_securities,
            'success_rate': successful_charts / total_charts if total_charts > 0 else 0
        }
    
    def render_waiting_dashboard(self):
        """
        渲染等待状态的多图看板
        """
        col_defs = [1, 1, 1]
        row1 = st.columns(col_defs)
        row2 = st.columns(col_defs)
        plot_positions = row1 + row2
        
        for i, pos in enumerate(plot_positions):
            with pos:
                st.markdown(
                    f"<div style='height: 400px; display: flex; align-items: center; "
                    f"justify-content: center; background-color: #f0f2f6; border-radius: 10px; "
                    f"text-align: center; color: grey;'>图表 {i+1}<br>等待分析...</div>", 
                    unsafe_allow_html=True
                )


# === 全局函数接口（向后兼容） ===

# 创建全局UI组件管理器实例
_ui_manager = UIComponentManager()

def run_single_chart_analysis_with_kdas(security_type, symbol, api_key=None, model="deepseek-r1", manual_dates=None):
    """
    使用kdas包的集成功能进行单图精细分析（全局函数接口，向后兼容）
    
    Args:
        security_type: 证券类型
        symbol: 证券代码
        api_key: AI API密钥
        model: AI模型名称
        manual_dates: 手动指定的日期字典，如果提供则不使用AI推荐
    
    Returns:
        分析结果字典
    """
    return _ui_manager.run_single_chart_analysis_with_kdas(
        security_type, symbol, api_key, model, manual_dates
    )

def run_multi_chart_analysis_with_kdas(securities_config, global_dates):
    """
    使用kdas包优化多图看板分析功能（全局函数接口，向后兼容）
    
    Args:
        securities_config: 证券配置列表
        global_dates: 全局日期配置
    
    Returns:
        分析结果列表
    """
    return _ui_manager.run_multi_chart_analysis_with_kdas(securities_config, global_dates)

def render_multi_chart_dashboard(analysis_results):
    """
    渲染多图看板的结果展示（全局函数接口，向后兼容）
    
    Args:
        analysis_results: 分析结果列表
    """
    return _ui_manager.render_multi_chart_dashboard(analysis_results)

def get_multi_chart_summary(analysis_results):
    """
    获取多图看板分析的汇总信息（全局函数接口，向后兼容）
    
    Args:
        analysis_results: 分析结果列表
    
    Returns:
        汇总信息字典
    """
    return _ui_manager.get_multi_chart_summary(analysis_results)

def render_waiting_dashboard():
    """
    渲染等待状态的多图看板（全局函数接口，向后兼容）
    """
    return _ui_manager.render_waiting_dashboard() 