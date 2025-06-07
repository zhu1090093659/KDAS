import os
import akshare as ak
import pandas as pd
'''
获取A股 个股，ETF，指数的接口
'''
# fund_etf_hist_em_df = ak.fund_etf_hist_em(symbol="159915", period="daily", start_date="20240101", end_date="20280801", adjust="qfq")#获取A股单个ETF数据

def get_etf_index():
    '''
    获取ETF信息
    '''
    os.makedirs('etfs', exist_ok=True)
    if os.path.exists('etfs\{}.csv'.format("A股全部ETF代码")):
        etf_info_df = pd.read_csv('etfs\{}.csv'.format("A股全部ETF代码"), dtype={0: str})
    else:
        etf_info_df = ak.fund_etf_spot_em()#东财A股全部ETF
        etf_info_df = etf_info_df[['代码', '名称']].drop_duplicates().rename(columns={"代码": "code", "名称": "name"})
        etf_info_df.to_csv('etfs\{}.csv'.format("A股全部ETF代码"), index=False)
    return etf_info_df

def get_share_index():
    '''
    获取个股信息
    '''
    os.makedirs('shares', exist_ok=True)
    if os.path.exists('shares\{}.csv'.format("A股全部个股代码")):
        share_info_df = pd.read_csv('shares\{}.csv'.format("A股全部个股代码"), dtype={0: str})
    else:
        share_info_df = ak.stock_info_a_code_name()
        share_info_df.to_csv('shares\{}.csv'.format("A股全部个股代码"), index=False)
    return share_info_df

def get_stock_index():
    '''
    获取指数信息
    '''
    os.makedirs('stocks', exist_ok=True)
    if os.path.exists('stocks\{}.csv'.format("A股全部指数代码")):
        stock_info_df = pd.read_csv('stocks\{}.csv'.format("A股全部指数代码"), dtype={0: str})
    else:

        categories = ("沪深重要指数", "上证系列指数", "深证系列指数", "指数成份", "中证系列指数")
        index_dfs = []
        for category in categories:
            df = ak.stock_zh_index_spot_em(symbol=category)
            index_dfs.append(df)
        # 合并数据并去重
        stock_info_df = pd.concat(index_dfs).drop_duplicates(subset=["代码"])
        stock_info_df = stock_info_df[["代码", "名称"]].rename(columns={"代码": "code", "名称": "name"})
        stock_info_df.to_csv('stocks\{}.csv'.format("A股全部指数代码"), index=False)
    return stock_info_df

if __name__ == "__main__":
    get_etf_index()
    get_share_index()
    get_stock_index()