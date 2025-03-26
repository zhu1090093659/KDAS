import yfinance as yf
import pandas as pd
import mplfinance as mpf
from datetime import datetime

# 获取股票数据（支持实时数据获取）
def get_stock_data(symbol, start_date):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=start_date, end=datetime.today().strftime('%Y-%m-%d'), interval='1d')
    hist['成交额'] = hist['Close'] * hist['Volume']  # 计算成交额（网页4）
    return hist

def calculate_dynamic_ma(data):
    # 累计计算成交额和成交量
    data['累计成交额'] = data['成交额'].cumsum()
    data['累计成交量'] = data['Volume'].cumsum()
    # 计算动态均线（网页1提到的加权平均法）
    data['动态均线'] = data['累计成交额'] / data['累计成交量']
    return data[['Open', 'High', 'Low', 'Close', 'Volume', '动态均线']]

def handle_realtime_data(symbol, existing_data):
    # 获取当日分钟级数据（网页6提到的实时数据获取）
    realtime = yf.Ticker(symbol).history(period='1d', interval='1m')
    if not realtime.empty:
        latest = realtime.iloc[-1]
        existing_data.loc[datetime.today().date()] = {
            'Open': latest['Open'], 'High': latest['High'],
            'Low': latest['Low'], 'Close': latest['Close'],
            'Volume': latest['Volume'], '成交额': latest['Close'] * latest['Volume']
        }
    return existing_data

def plot_chart(data, symbol):
    # 创建附加绘图对象（网页4的K线图绘制方法）
    apd = mpf.make_addplot(data['动态均线'], color='purple', width=2)
    
    # 设置绘图样式
    mc = mpf.make_marketcolors(up='r', down='g', wick='i', edge='i', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    
    # 绘制带均线的K线图（网页4的绘图示例扩展）
    mpf.plot(data, type='candle', style=s, addplot=apd,
             title=f'{symbol} 动态均线分析',
             ylabel='价格',
             volume=True,
             datetime_format='%Y-%m',
             show_nontrading=False)

# 主程序
if __name__ == "__main__":
    symbol = '宜安科技'  # 示例股票代码
    start_date = '2025-09-26'  # 示例起始日期
    
    # 获取基础数据
    data = get_stock_data(symbol, start_date)
    
    # 处理实时数据
    if datetime.today().date() in data.index:
        data = handle_realtime_data(symbol, data)
    
    # 计算动态均线
    processed_data = calculate_dynamic_ma(data)
    
    # 可视化展示
    plot_chart(processed_data, symbol)