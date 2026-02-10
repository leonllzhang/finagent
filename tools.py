import tushare as ts
import pandas as pd
import pandas_ta as ta
import os
from config import Config

# 初始化 tushare
pro = ts.pro_api(Config.TUSHARE_TOKEN)

def fetch_etf_metrics_5min(ts_code: str):
    """
    使用 Tushare 获取 5 分钟 K 线数据
    ts_code: 格式为 '510300.SH'
    """
    try:
        # 1. 获取 5 分钟数据 (使用 pro_bar 接口)
        # asset='FD' 代表基金(ETF)
        df = ts.pro_bar(
            ts_code=ts_code, 
            asset='FD', 
            freq='5min', 
            start_date='', # 留空会自动取最近
            end_date=''
        )

        if df is None or df.empty:
            raise ValueError(f"Tushare 未返回数据，请检查积分是否足够或代码 {ts_code} 是否正确")

        # Tushare 返回的数据是倒序的（最新在第一行），我们需要正序计算指标
        df = df.sort_values('trade_time').copy()

        # 2. 统一列名以适配 pandas_ta (Tushare 默认是 lowercase)
        df = df.rename(columns={
            'vol': 'volume',
            'trade_time': 'datetime'
        })
        
        # 3. 计算技术指标
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        
        # 计算量比 (当前5分钟量 / 过去20个5分钟均量)
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()

        # 4. 提取当前和上一周期的快照
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # 5. 获取 ETF 名称 (fund_basic 接口)
        basic_info = pro.fund_basic(ts_code=ts_code)
        name = basic_info.iloc[0]['name'] if not basic_info.empty else ts_code

        return {
            "name": name,
            "time": curr['datetime'],
            "price": curr['close'],
            "prev_price": prev['close'],
            "price_chg_5m": ((curr['close'] - prev['close']) / prev['close']) * 100,
            "rsi": curr['RSI'],
            "rsi_prev": prev['RSI'],
            "macd_hist": curr['MACDh_12_26_9'],
            "macd_hist_prev": prev['MACDh_12_26_9'],
            "vol_ratio": curr['vol_ratio'],
            "is_red": curr['close'] > curr['open']
        }

    except Exception as e:
        print(f"❌ Tushare 采集报错: {e}")
        raise e