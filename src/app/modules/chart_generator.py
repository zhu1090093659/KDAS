"""
KDAS证券分析工具 - 图表生成模块

该模块负责生成各种类型的交互式图表，包括：
- 单图精细分析的完整图表
- 多图看板的紧凑型图表
- 支撑位和压力位计算
- 图表样式和布局配置

主要功能：
1. create_interactive_chart: 创建完整的交互式K线图和KDAS指标图表
2. create_mini_chart: 创建紧凑型图表，用于多图看板
3. _calculate_support_resistance: 计算支撑位和压力位
4. _create_legend_text: 创建图例文本
5. _apply_chart_styling: 应用图表样式和布局

技术栈：
- plotly: 交互式图表库
- pandas: 数据处理

作者：KDAS团队
版本：2.0 (模块化重构版本)
"""

# === 标准库导入 ===
from datetime import datetime

# === 第三方库导入 ===
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# === 本地模块导入 ===
try:
    from .data_handler import get_non_trading_dates
except ImportError:
    # 备用导入方案
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from data_handler import get_non_trading_dates


class ChartGenerator:
    """图表生成器类，负责创建各种类型的KDAS分析图表"""
    
    def __init__(self):
        """初始化图表生成器"""
        # KDAS线条颜色配置
        self.kdas_colors = {
            'day1': "#FF0000",   # 红色
            'day2': "#0000FF",   # 蓝色  
            'day3': "#00FF00",   # 绿色
            'day4': "#FF00FF",   # 紫色
            'day5': "#FFA500",   # 橙色
        }
        
        # 图表样式配置
        self.chart_config = {
            'candlestick_colors': {
                'increasing_line': '#FF4444',
                'decreasing_line': '#00AA00',
                'increasing_fill': '#FF4444',
                'decreasing_fill': '#00AA00'
            },
            'template': 'plotly_white',
            'font_family': 'monospace'
        }
    
    def create_interactive_chart(self, df, input_date, info_df, security_type="股票", symbol_code=None):
        """
        创建交互式图表，用于单图精细分析
        
        Args:
            df: 包含KDAS计算结果的证券数据DataFrame
            input_date: 输入日期字典，格式为 {'day1': 'YYYYMMDD', ...}
            info_df: 证券信息DataFrame，包含代码和名称映射
            security_type: 证券类型（股票、ETF、指数）
            symbol_code: 证券代码
            
        Returns:
            plotly.graph_objects.Figure: 交互式图表对象
        """
        # 创建子图：上方K线图+KDAS，下方成交量
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=('K线图与KDAS指标', '成交量'),
            row_heights=[0.75, 0.25]  # 上图占75%，下图占25%
        )
        
        # 数据预处理和验证
        df = self._preprocess_data(df)
        
        # 获取证券名称
        security_name = self._get_security_name(df, info_df, security_type, symbol_code)
        symbol_code = self._extract_symbol_code(df, symbol_code)
        
        # 添加K线图
        self._add_candlestick_chart(fig, df, security_name, row=1, col=1)
        
        # 添加KDAS线条
        self._add_kdas_lines(fig, df, input_date, row=1, col=1)
        
        # 添加成交量图
        self._add_volume_chart(fig, df, row=2, col=1)
        
        # 设置Y轴标题
        fig.update_yaxes(title_text="价格/KDAS (元)", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)
        fig.update_xaxes(title_text="日期", row=2, col=1)
        
        # 计算支撑位和压力位
        support_levels, resistance_levels = self._calculate_support_resistance(df, input_date)
        
        # 创建图例文本
        legend_text = self._create_legend_text(df, support_levels, resistance_levels)
        
        # 应用图表样式和布局
        self._apply_chart_styling(
            fig, security_name, symbol_code, legend_text, 
            height=800, font_size=11, is_mini=False
        )
        
        # 配置时间轴（跳过非交易日）
        self._configure_time_axis(fig, df)
        
        # 设置Y轴范围
        self._set_y_axis_range(fig, df, input_date, row=1, col=1)
        
        return fig
    
    def create_mini_chart(self, df, input_date, info_df, security_type="股票", symbol_code=None):
        """
        创建紧凑型交互式图表，用于多图看板
        
        Args:
            df: 包含KDAS计算结果的证券数据DataFrame
            input_date: 输入日期字典，格式为 {'day1': 'YYYYMMDD', ...}
            info_df: 证券信息DataFrame，包含代码和名称映射
            security_type: 证券类型（股票、ETF、指数）
            symbol_code: 证券代码
            
        Returns:
            plotly.graph_objects.Figure: 紧凑型图表对象
        """
        # 创建子图：主要是K线图+KDAS
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=(None, None),  # 不显示子图标题
            row_heights=[0.7, 0.3]
        )
        
        # 数据预处理（简化版）
        df = self._preprocess_data_mini(df)
        
        # 获取证券名称
        security_name = self._get_security_name(df, info_df, security_type, symbol_code)
        symbol_code = self._extract_symbol_code(df, symbol_code)
        
        # 添加K线图
        self._add_candlestick_chart(fig, df, security_name, row=1, col=1)
        
        # 添加KDAS线条
        self._add_kdas_lines(fig, df, input_date, row=1, col=1)
        
        # 计算支撑位和压力位
        support_levels, resistance_levels = self._calculate_support_resistance(df, input_date)
        
        # 创建图例文本
        legend_text = self._create_legend_text(df, support_levels, resistance_levels)
        
        # 应用紧凑型图表样式
        self._apply_chart_styling(
            fig, security_name, symbol_code, legend_text,
            height=400, font_size=9, is_mini=True
        )
        
        # 配置时间轴
        self._configure_time_axis_mini(fig, df)
        
        # 设置Y轴范围
        self._set_y_axis_range(fig, df, input_date, row=1, col=1)
        
        # 移除Y轴标题（紧凑型图表）
        fig.update_yaxes(title_text=None, row=1, col=1)
        fig.update_yaxes(title_text=None, row=2, col=1)
        
        return fig
    
    def _preprocess_data(self, df):
        """
        数据预处理和验证（完整版）
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            DataFrame: 预处理后的数据
        """
        df = df.copy()  # 避免修改原始数据
        
        # 确保数据按日期排序
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
        
        return df
    
    def _preprocess_data_mini(self, df):
        """
        数据预处理（简化版，用于紧凑型图表）
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            DataFrame: 预处理后的数据
        """
        df = df.copy()
        df = df.sort_values('日期').reset_index(drop=True)
        df = df.dropna(subset=['开盘', '收盘', '最高', '最低', '成交量', '成交额'])
        df = df[df['成交量'] > 0].reset_index(drop=True)
        df = df[(df['开盘'] > 0) & (df['收盘'] > 0) & (df['最高'] > 0) & (df['最低'] > 0)].reset_index(drop=True)
        df = df[df['最高'] >= df['最低']].reset_index(drop=True)
        
        return df
    
    def _get_security_name(self, df, info_df, security_type, symbol_code):
        """
        获取证券名称
        
        Args:
            df: 数据DataFrame
            info_df: 证券信息DataFrame
            security_type: 证券类型
            symbol_code: 证券代码
            
        Returns:
            str: 证券名称
        """
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
        security_name_series = info_df[info_df["code"] == symbol_code]["name"]
        security_name = security_name_series.values[0] if len(security_name_series) > 0 else f"未知{security_type}"
        
        return security_name
    
    def _extract_symbol_code(self, df, symbol_code):
        """
        提取并标准化证券代码
        
        Args:
            df: 数据DataFrame
            symbol_code: 原始证券代码
            
        Returns:
            str: 标准化的证券代码
        """
        if symbol_code is None:
            if '股票代码' in df.columns:
                symbol_code = df['股票代码'].iloc[0]
            else:
                symbol_code = df.iloc[0, 0] if len(df.columns) > 0 else "未知代码"
        
        return str(symbol_code).split('.')[0]
    
    def _add_candlestick_chart(self, fig, df, security_name, row, col):
        """
        添加K线图到指定位置
        
        Args:
            fig: plotly图表对象
            df: 数据DataFrame
            security_name: 证券名称
            row: 行位置
            col: 列位置
        """
        fig.add_trace(go.Candlestick(
            x=df['日期'],
            open=df['开盘'],
            high=df['最高'],
            low=df['最低'],
            close=df['收盘'],
            name=f'{security_name}',
            increasing_line_color=self.chart_config['candlestick_colors']['increasing_line'],
            decreasing_line_color=self.chart_config['candlestick_colors']['decreasing_line'],
            increasing_fillcolor=self.chart_config['candlestick_colors']['increasing_fill'],
            decreasing_fillcolor=self.chart_config['candlestick_colors']['decreasing_fill'],
            showlegend=False
        ), row=row, col=col)
    
    def _add_kdas_lines(self, fig, df, input_date, row, col):
        """
        添加KDAS线条到指定位置
        
        Args:
            fig: plotly图表对象
            df: 数据DataFrame
            input_date: 输入日期字典
            row: 行位置
            col: 列位置
        """
        for key, value in input_date.items():
            if f'KDAS{value}' in df.columns:
                # 过滤掉NaN值
                mask = df[f'KDAS{value}'].notna()
                fig.add_trace(go.Scatter(
                    x=df.loc[mask, '日期'],
                    y=df.loc[mask, f'KDAS{value}'],
                    mode='lines',
                    name=f'D{key[-1]}',
                    line=dict(
                        color=self.kdas_colors.get(key, "#000000"), 
                        width=2, 
                        dash='solid'
                    ),
                    opacity=0.8
                ), row=row, col=col)
    
    def _add_volume_chart(self, fig, df, row, col):
        """
        添加成交量图到指定位置
        
        Args:
            fig: plotly图表对象
            df: 数据DataFrame
            row: 行位置
            col: 列位置
        """
        # 根据涨跌设置成交量颜色
        volume_colors = [
            self.chart_config['candlestick_colors']['increasing_line'] if close >= open 
            else self.chart_config['candlestick_colors']['decreasing_line']
            for close, open in zip(df['收盘'], df['开盘'])
        ]
        
        fig.add_trace(go.Bar(
            x=df['日期'],
            y=df['成交量'],
            name='成交量',
            marker_color=volume_colors,
            opacity=0.7,
            showlegend=False
        ), row=row, col=col)
    
    def _calculate_support_resistance(self, df, input_date):
        """
        计算当前支撑位和压力位
        
        Args:
            df: 数据DataFrame
            input_date: 输入日期字典
            
        Returns:
            tuple: (支撑位列表, 压力位列表)
        """
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
        
        return support_levels, resistance_levels
    
    def _create_legend_text(self, df, support_levels, resistance_levels):
        """
        创建图例文本
        
        Args:
            df: 数据DataFrame
            support_levels: 支撑位列表
            resistance_levels: 压力位列表
            
        Returns:
            list: 图例文本列表
        """
        current_price = df['收盘'].iloc[-1]
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
        
        return legend_text
    
    def _apply_chart_styling(self, fig, security_name, symbol_code, legend_text, 
                           height=800, font_size=11, is_mini=False):
        """
        应用图表样式和布局
        
        Args:
            fig: plotly图表对象
            security_name: 证券名称
            symbol_code: 证券代码
            legend_text: 图例文本列表
            height: 图表高度
            font_size: 字体大小
            is_mini: 是否为紧凑型图表
        """
        # 设置标题
        if is_mini:
            title_text = f"{security_name} ({symbol_code})"
            title_font_size = 14
        else:
            title_text = f"{security_name} ({symbol_code}) - K线走势图与KDAS指标分析"
            title_font_size = 16
        
        # 设置边距
        margin_config = dict(l=40, r=20, t=70, b=40) if is_mini else dict()
        
        # 更新整体布局
        fig.update_layout(
            title={
                'text': title_text,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': title_font_size}
            },
            height=height,
            xaxis_rangeslider_visible=False,  # 隐藏K线图下方的范围滑块
            showlegend=False,  # 隐藏默认图例
            hovermode='x unified',  # 统一悬停模式
            template=self.chart_config['template'],  # 使用白色主题
            margin=margin_config,
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
                    font=dict(size=font_size, family=self.chart_config['font_family']),
                    align="left",
                    xanchor="left",
                    yanchor="top"
                )
            ]
        )
    
    def _configure_time_axis(self, fig, df):
        """
        配置时间轴，跳过非交易日（完整版）
        
        Args:
            fig: plotly图表对象
            df: 数据DataFrame
        """
        # 使用官方交易日历配置X轴，精确跳过非交易日
        # 基础配置：隐藏周末
        rangebreaks_config = [
            dict(bounds=["sat", "mon"])  # 隐藏周末
        ]
        
        # 获取数据的日期范围
        start_date = df['日期'].min().date()
        end_date = df['日期'].max().date()
        
        # 使用官方交易日历获取非交易日
        try:
            non_trading_dates = get_non_trading_dates(start_date, end_date)
            
            if non_trading_dates:
                rangebreaks_config.append(dict(values=non_trading_dates))
                print(f"🗓️ 应用了 {len(non_trading_dates)} 个非交易日的rangebreaks配置")
            else:
                print("⚠️ 未获取到非交易日数据，仅应用周末配置")
        except Exception as e:
            print(f"⚠️ 获取非交易日数据失败: {e}，仅应用周末配置")
        
        # 应用配置到两个子图
        fig.update_xaxes(rangebreaks=rangebreaks_config, row=1, col=1)
        fig.update_xaxes(rangebreaks=rangebreaks_config, row=2, col=1)
    
    def _configure_time_axis_mini(self, fig, df):
        """
        配置时间轴（紧凑型图表版本）
        
        Args:
            fig: plotly图表对象
            df: 数据DataFrame
        """
        start_date, end_date = df['日期'].min().date(), df['日期'].max().date()
        
        rangebreaks_config = [dict(bounds=["sat", "mon"])]
        
        try:
            non_trading_dates = get_non_trading_dates(start_date, end_date)
            if non_trading_dates:
                rangebreaks_config.append(dict(values=non_trading_dates))
        except Exception:
            pass  # 静默处理错误，使用基础配置
        
        fig.update_xaxes(rangebreaks=rangebreaks_config)
    
    def _set_y_axis_range(self, fig, df, input_date, row, col):
        """
        设置Y轴范围，综合考虑价格和KDAS值
        
        Args:
            fig: plotly图表对象
            df: 数据DataFrame
            input_date: 输入日期字典
            row: 行位置
            col: 列位置
        """
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
            row=row, col=col
        )


# === 全局函数接口（向后兼容） ===

# 创建全局图表生成器实例
_chart_generator = ChartGenerator()

def create_interactive_chart(df, input_date, info_df, security_type="股票", symbol_code=None):
    """
    创建交互式图表（全局函数接口，向后兼容）
    
    Args:
        df: 包含KDAS计算结果的证券数据DataFrame
        input_date: 输入日期字典，格式为 {'day1': 'YYYYMMDD', ...}
        info_df: 证券信息DataFrame，包含代码和名称映射
        security_type: 证券类型（股票、ETF、指数）
        symbol_code: 证券代码
        
    Returns:
        plotly.graph_objects.Figure: 交互式图表对象
    """
    return _chart_generator.create_interactive_chart(
        df, input_date, info_df, security_type, symbol_code
    )

def create_mini_chart(df, input_date, info_df, security_type="股票", symbol_code=None):
    """
    创建紧凑型交互式图表（全局函数接口，向后兼容）
    
    Args:
        df: 包含KDAS计算结果的证券数据DataFrame
        input_date: 输入日期字典，格式为 {'day1': 'YYYYMMDD', ...}
        info_df: 证券信息DataFrame，包含代码和名称映射
        security_type: 证券类型（股票、ETF、指数）
        symbol_code: 证券代码
        
    Returns:
        plotly.graph_objects.Figure: 紧凑型图表对象
    """
    return _chart_generator.create_mini_chart(
        df, input_date, info_df, security_type, symbol_code
    )