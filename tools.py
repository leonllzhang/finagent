import requests
import pandas as pd
import pandas_ta as ta
import os
import re
import json
from datetime import datetime

os.environ['no_proxy'] = '*'

class SinaFinanceAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }

    def get_kline(self, symbol, scale=5, datalen=100):
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
        except:
            return pd.DataFrame()

def fetch_etf_enhanced_metrics(symbol: str):
    api = SinaFinanceAPI()
    # 5分钟线（多取一点用于VWAP重置计算）
    df_5m = api.get_kline(symbol, scale=5, datalen=240)
    if df_5m.empty: raise ValueError(f"无法获取数据")

    # VWAP 计算 (每日重置)
    df_5m['date_only'] = df_5m['day'].str[:10]
    df_5m['tp'] = (df_5m['high'] + df_5m['low'] + df_5m['close']) / 3
    df_5m['pv'] = df_5m['tp'] * df_5m['volume']
    df_5m['cum_pv'] = df_5m.groupby('date_only')['pv'].cumsum()
    df_5m['cum_vol'] = df_5m.groupby('date_only')['volume'].cumsum()
    df_5m['vwap'] = df_5m['cum_pv'] / df_5m['cum_vol']

    # 基础指标
    df_5m['RSI'] = ta.rsi(df_5m['close'], length=14)
    macd = ta.macd(df_5m['close'])
    df_5m = pd.concat([df_5m, macd], axis=1)
    df_5m['macd_slope'] = df_5m['MACDh_12_26_9'].diff()
    
    # 布林带
    bb = ta.bbands(df_5m['close'], length=20, std=2)
    df_5m = pd.concat([df_5m, bb], axis=1)
    df_5m['vol_ratio'] = df_5m['volume'] / df_5m['volume'].rolling(20).mean()

    # 日线趋势
    df_daily = api.get_kline(symbol, scale=240, datalen=60)
    curr_d = df_daily.iloc[-1] if not df_daily.empty else None

    # 大盘
    df_market = api.get_kline("000300", scale=5, datalen=2)
    market_pct = ((df_market['close'].iloc[-1] - df_market['close'].iloc[0]) / df_market['close'].iloc[0]) * 100 if not df_market.empty else 0

    curr = df_5m.iloc[-1]
    prev = df_5m.iloc[-2]

    # 布林带位置
    if curr['close'] > curr['BBU_20_2.0']: bb_status = "向上突破上轨"
    elif curr['close'] < curr['BBL_20_2.0']: bb_status = "向下跌破下轨"
    else: bb_status = "轨道内波动"

    return {
        "name": symbol, "time": curr['day'], "price": curr['close'],
        "chg_5m": ((curr['close'] - prev['close']) / prev['close']) * 100,
        "rsi_5m": curr['RSI'], "macd_hist_5m": curr['MACDh_12_26_9'],
        "macd_slope": curr['macd_slope'], "macd_slope_desc": "增强" if curr['macd_slope'] > 0 else "减弱",
        "vol_ratio_5m": curr['vol_ratio'], "bb_status": bb_status,
        "bb_upper": curr['BBU_20_2.0'], "bb_lower": curr['BBL_20_2.0'], "bb_mid": curr['BBM_20_2.0'],
        "vwap": curr['vwap'], "vwap_dist": ((curr['close'] - curr['vwap']) / curr['vwap']) * 100,
        "vwap_status": "VWAP上方" if curr['close'] > curr['vwap'] else "VWAP下方",
        "daily_trend": "多头" if (curr_d is not None and curr_d['close'] > ta.sma(df_daily['close'], 20).iloc[-1]) else "空头",
        "market_index_pct": market_pct,
        "daily_rsi": curr_d['RSI'] if curr_d is not None else 50
    }