import requests
import pandas as pd
import pandas_ta as ta
import os
import re
import json
from datetime import datetime

# 强力直连，禁用代理
os.environ['no_proxy'] = '*'

class SinaFinanceAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }

    def get_kline(self, symbol, scale=5, datalen=100):
        """
        获取K线数据
        scale: 分钟数 (5, 15, 30, 60); 240代表日线
        datalen: 获取多少根K线
        """
        market = "sh" if symbol.startswith(("5", "6", "000300")) else "sz"
        full_symbol = f"{market}{symbol}"
        url = f"https://quotes.sina.cn/cn/api/jsonp.php/var_{full_symbol}_{scale}/CN_MarketDataService.getKLineData?symbol={full_symbol}&scale={scale}&ma=no&datalen={datalen}"
        
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            match = re.search(r'\[.*\]', res.text)
            if not match: return pd.DataFrame()
            
            df = pd.DataFrame(json.loads(match.group()))
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            return df
        except Exception as e:
            print(f"Sina API Error ({symbol}): {e}")
            return pd.DataFrame()

def fetch_etf_enhanced_metrics(symbol: str):
    api = SinaFinanceAPI()
    
    # 1. 获取 5 分钟 K 线 (择时)
    df_5m = api.get_kline(symbol, scale=5, datalen=100)
    if df_5m.empty: raise ValueError(f"无法获取 {symbol} 5分钟数据")
    
    # 计算 5 分钟指标
    df_5m['RSI'] = ta.rsi(df_5m['close'], length=14)
    macd_5 = ta.macd(df_5m['close'])
    df_5m = pd.concat([df_5m, macd_5], axis=1)
    df_5m['vol_ratio'] = df_5m['volume'] / df_5m['volume'].rolling(20).mean() # 5min量比

    # 2. 获取 日线 K 线 (趋势)
    df_daily = api.get_kline(symbol, scale=240, datalen=60)
    df_daily['MA20'] = ta.sma(df_daily['close'], length=20)
    df_daily['RSI'] = ta.rsi(df_daily['close'], length=14)

    # 3. 获取大盘参考 (沪深300 - 000300)
    df_market = api.get_kline("000300", scale=5, datalen=2)
    market_pct = ((df_market['close'].iloc[-1] - df_market['close'].iloc[0]) / df_market['close'].iloc[0]) * 100

    # 提取关键点
    curr_5m = df_5m.iloc[-1]
    prev_5m = df_5m.iloc[-2]
    curr_d = df_daily.iloc[-1]

    return {
        "name": symbol, # 简单处理
        "time": curr_5m['day'],
        # 5min数据
        "price": curr_5m['close'],
        "chg_5m": ((curr_5m['close'] - prev_5m['close']) / prev_5m['close']) * 100,
        "rsi_5m": curr_5m['RSI'],
        "macd_hist_5m": curr_5m['MACDh_12_26_9'],
        "vol_ratio_5m": curr_5m['vol_ratio'],
        # 日线趋势数据
        "daily_trend": "多头" if curr_d['close'] > curr_d['MA20'] else "空头",
        "daily_rsi": curr_d['RSI'],
        # 大盘环境
        "market_index_pct": market_pct
    }