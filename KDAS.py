import os
import akshare as ak
import pandas as pd
from datetime import datetime
from pyecharts.charts import Kline
from pyecharts.charts import Line
from pyecharts import options as opts
from pyecharts.charts import Bar
from pyecharts.commons.utils import JsCode
from pyecharts.charts import Grid

if os.path.exists('shares\{}.csv'.format("A股全部股票代码")):
    stock_info_df = pd.read_csv('shares\{}.csv'.format("A股全部股票代码"), dtype={0: str})
else:
    stock_info_df = ak.stock_info_a_code_name()
    stock_info_df.to_csv('shares\{}.csv'.format("A股全部股票代码"), index=False)
# 获取A股历史数据（含成交额）
def get_a_stock_data(symbol, input_date):
    # 转换代码格式（如300328.SZ -> 300328）
    symbol = symbol.split('.')[0]
    start_date = min(input_date.values())
    today = datetime.now().strftime('%Y%m%d') #20250326
    if os.path.exists('shares\{}.csv'.format(symbol)):
        df = pd.read_csv('shares\{}.csv'.format(symbol))
        if not pd.to_datetime(start_date) in df['日期'].iloc: #csv数据不包括start_date，全部更新数据
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, adjust="qfq") 
            df.to_csv('shares\{}.csv'.format(symbol), index=False)
        elif df['日期'].iloc[-1] < pd.to_datetime(datetime.now()): #csv最新日期小于时间戳，获取最新的数据，追加在后面
            df_add = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=df['日期'].iloc[-1].strftime('%Y%m%d'), adjust="qfq")
            df.drop(index=df.index[-1], inplace=True)
            df = pd.concat([df, df_add], ignore_index=True)
            df.to_csv('shares\{}.csv'.format(symbol), index=False)
    else:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, adjust="qfq") 
        df.to_csv('shares\{}.csv'.format(symbol), index=False)
    return df

# KDAS计算
def calculate_cumulative_vwap(df, input_date):
    for key,value in input_date.items():
        df['累计成交额{}'.format(value)] = df['成交额'].iloc[df[df['日期'] == datetime.strptime(value, "%Y%m%d").date()].index[0]:].cumsum()
        df['累计成交量{}'.format(value)] = df['成交量'].iloc[df[df['日期'] == datetime.strptime(value, "%Y%m%d").date()].index[0]:].cumsum()
        df['KDAS{}'.format(value)] = (df['累计成交额{}'.format(value)] / df['累计成交量{}'.format(value)] / 100).round(2) #保留2位小数
    return df

def plot_kline_with_kdas(df, input_date):
    kline = Kline()
    df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d') 
    df = df.sort_values("日期") # 安装日期排序
    data = df[["开盘", "收盘", "最低", "最高"]].values.tolist()
    kline.add_xaxis(df['日期'].tolist())  # X轴日期数据
    kline.add_yaxis(
        series_name="k线",  # y轴名称
        y_axis=data,  # K线数据序列
        itemstyle_opts=opts.ItemStyleOpts(
            color="#ef232a",    # 上涨颜色（红色）
            color0="#14b143",   # 下跌颜色（绿色）
            border_color="#000",  # 统一黑色描边
            border_color0="#000"
        )
    )
    kline.set_global_opts(
        title_opts=opts.TitleOpts(title="股票K线走势图+KDAS画线", subtitle=stock_info_df[stock_info_df["code"] == df['股票代码'][0]]["name"].values[0]+df['股票代码'][0]),
        xaxis_opts=opts.AxisOpts(
            type_='category',
            axislabel_opts=opts.LabelOpts(rotate=45),  # 日期标签旋转45度
            splitline_opts=opts.SplitLineOpts(is_show=True)  # 显示网格线
        ),
        yaxis_opts=opts.AxisOpts(
            splitarea_opts=opts.SplitAreaOpts(
                is_show=True, 
                areastyle_opts=opts.AreaStyleOpts(opacity=1)
            ),is_scale=True # 启用自动缩放
        ),
        tooltip_opts=opts.TooltipOpts(
            trigger="axis",
            axis_pointer_type="cross",
            background_color="rgba(245, 245, 245, 0.8)",
            border_width=1,
            border_color="#ccc",
            textstyle_opts=opts.TextStyleOpts(color="#000"),
        ),
        # visualmap_opts=opts.VisualMapOpts(
        #     is_show=False,
        #     dimension=2,
        #     series_index=5,
        #     is_piecewise=True,
        #     pieces=[
        #         {"value": 1, "color": "#00da3c"},
        #         {"value": -1, "color": "#ec0000"},
        #     ],
        # ),
        brush_opts=opts.BrushOpts(
            x_axis_index="all",
            brush_link="all",
            out_of_brush={"colorAlpha": 0.1},
            brush_type="lineX",
        ),
        datazoom_opts=[  # 添加数据缩放控件
            opts.DataZoomOpts(
                is_show=False,
                type_="inside",
                xaxis_index=[0],
                range_start=50,
                range_end=100
            ),
            opts.DataZoomOpts(
                is_show=False,
                xaxis_index=[0],
                type_="slider",
                pos_top="80%",
                range_start=50,
                range_end=100
            )
        ]
    )

    line = Line()
    kdas_colors = {
        'day1': {"color": "#FF0000", "width": 2},   
        'day2': {"color": "#0000FF", "width": 2},  
        'day3': {"color": "#00FF00", "width": 2},   
        'day4': {"color": "#ff00f7", "width": 2},   
        'day5': {"color": "#f2ee69", "width": 2},   
    }
    line.add_xaxis(df['日期'].tolist())
    for key, value in input_date.items():
            line.add_yaxis(
                series_name="KDAS:{}".format(value),
                y_axis=df['KDAS{}'.format(value)].tolist(),
                is_smooth=True,
                is_hover_animation=False,
                linestyle_opts=opts.LineStyleOpts(width=3, opacity=0.5),
                label_opts=opts.LabelOpts(is_show=False),
            ).set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
    overlap_kline = kline.overlap(line)

    df['color'] = df.apply(lambda x: "#ef232a" if x['收盘'] >= x['开盘'] else "#14b143", axis=1)
    vol_bar = (
        Bar()
        .add_xaxis(df['日期'].tolist())
        .add_yaxis(
            series_name="",
            
            y_axis=df['成交量'].tolist(),
            itemstyle_opts=opts.ItemStyleOpts(
                color=JsCode('''
                    function(params) {
                        var colors = [%s];  
                        return params.dataIndex < colors.length ? colors[params.dataIndex] : '#14b143';
                    }
                ''' % ("'" + "','".join(df['color'].tolist()) + "'"))  # 生成正确数组格式
            ),
            yaxis_index=1,
            bar_width='60%',
            label_opts=opts.LabelOpts(is_show=False)
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                axislabel_opts=opts.LabelOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False)
            ),
            yaxis_opts=opts.AxisOpts(
                position="right",
                axislabel_opts=opts.LabelOpts(formatter=JsCode(
                    "function(value){return value > 10000 ? (value/10000).toFixed(1)+'万' : value;}"))
            )
        )
    )
    grid = (
        Grid(init_opts=opts.InitOpts(width="1200px", height="800px"))
        .add(
            overlap_kline,  # 使用已合并的K线均线图
            grid_opts=opts.GridOpts(
                pos_left="10%", 
                pos_right="8%", 
                height="50%",  # 主图高度65%
                # pos_top="10%"
            )
        )
        .add(
            vol_bar,
            grid_opts=opts.GridOpts(
                pos_left="10%",
                pos_right="8%",
                height="16%",  # 成交量图高度15%
                pos_top="65%"  # 从60%位置开始
            )
        )
    )
    grid.render("{}_KDAS.html".format(stock_info_df[stock_info_df["code"] == df['股票代码'][0]]["name"].values[0])) 

# 主程序
if __name__ == "__main__":
    symbol = '001215'  
    input_date = {
        'day1': '20240923',
        'day2': "20241107",
        'day3': "20241217",
        'day4': "20250102",
        'day5': "20250113"
    }				
    data = get_a_stock_data(symbol, input_date)  
    processed_data = calculate_cumulative_vwap(data, input_date)  
    plot_kline_with_kdas(processed_data, input_date)