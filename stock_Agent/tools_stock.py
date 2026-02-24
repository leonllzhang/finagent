import requests
import pandas as pd
import pandas_ta as ta
import os
import re
import json

# 强力直连，禁用代理
os.environ['no_proxy'] = '*'

class SinaStockAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }

    def get_market_prefix(self, symbol):
        """精准判定 A 股市场前缀"""
        if symbol.startswith(('6', '5')):
            return "sh"
        elif symbol.startswith(('0', '3', '1')):
            return "sz"
        return "sh"

    def get_kline(self, symbol, scale=5, datalen=240):
        market = self.get_market_prefix(symbol)
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
        except: return pd.DataFrame()

    def get_snapshot(self, symbol):
        """从腾讯获取个股实时快照（含换手率）"""
        market = self.get_market_prefix(symbol)
        url = f"http://qt.gtimg.cn/q={market}{symbol}"
        try:
            res = requests.get(url, timeout=5).text
            if len(res) < 50: return None
            p = res.split('~')
            return {
                "name": p[1], "price": float(p[3]), "last_close": float(p[4]),
                "turnover": float(p[38]) if p[38] else 0,
                "bid1_vol": int(p[10]) if p[10] else 0,
                "ask1_vol": int(p[20]) if p[20] else 0
            }
        except: return None

def fetch_stock_full_metrics(symbol, sector_symbol):
    api = SinaStockAPI()
    snap = api.get_snapshot(symbol)
    df_5m = api.get_kline(symbol, scale=5, datalen=240)
    
    if df_5m.empty or snap is None:
        raise ValueError(f"数据获取失败: {symbol}")

    # 1. VWAP 计算 (每日重置)
    df_5m['date_only'] = df_5m['day'].str[:10]
    df_5m['tp'] = (df_5m['high'] + df_5m['low'] + df_5m['close']) / 3
    df_5m['pv'] = df_5m['tp'] * df_5m['volume']
    df_5m['cum_pv'] = df_5m.groupby('date_only')['pv'].cumsum()
    df_5m['cum_vol'] = df_5m.groupby('date_only')['volume'].cumsum()
    df_5m['vwap'] = df_5m['cum_pv'] / df_5m['cum_vol']

    # 2. 技术指标计算
    df_5m['RSI'] = ta.rsi(df_5m['close'], length=14)
    macd = ta.macd(df_5m['close'])
    df_5m = pd.concat([df_5m, macd], axis=1)
    
    # 动态获取 MACD 柱线列名并计算斜率
    hist_col = [c for c in df_5m.columns if 'MACDh' in c][0]
    df_5m['macd_slope'] = df_5m[hist_col].diff().fillna(0)
    
    # 布林带动态识别
    bb = ta.bbands(df_5m['close'], length=20, std=2)
    df_5m = pd.concat([df_5m, bb], axis=1)
    upper_col = [c for c in df_5m.columns if 'BBU' in c][0]
    lower_col = [c for c in df_5m.columns if 'BBL' in c][0]
    mid_col = [c for c in df_5m.columns if 'BBM' in c][0]
    
    # 量比计算 (增加 min_periods 防止早盘 NaN)
    df_5m['vol_ratio'] = df_5m['volume'] / df_5m['volume'].rolling(window=20, min_periods=1).mean()
    df_5m['vol_ratio'] = df_5m['vol_ratio'].fillna(1.0)

    # 3. 板块对比
    sector_df = api.get_kline(sector_symbol, scale=5, datalen=2)
    sector_pct = ((sector_df['close'].iloc[-1] - sector_df['close'].iloc[0])/sector_df['close'].iloc[0]*100) if len(sector_df)>=2 else 0

    curr = df_5m.iloc[-1]
    prev = df_5m.iloc[-2]

    # 涨停空间
    limit_rate = 1.2 if symbol.startswith(("3", "68")) else 1.1
    upper_limit = round(snap['last_close'] * limit_rate, 2)

    return {
        "name": snap['name'], "time": curr['day'], "price": snap['price'],
        "chg_5m": ((snap['price'] - prev['close']) / prev['close'] * 100),
        "rsi_5m": curr['RSI'], "macd_hist_5m": curr[hist_col],
        "macd_slope": curr['macd_slope'], "macd_slope_desc": "增强" if curr['macd_slope'] > 0 else "减弱",
        "vol_ratio": curr['vol_ratio'],
        "bb_status": "向上突破" if snap['price'] > curr[upper_col] else "向下破位" if snap['price'] < curr[lower_col] else "轨道内",
        "bb_upper": curr[upper_col], "bb_lower": curr[lower_col], "bb_mid": curr[mid_col],
        "vwap": curr['vwap'], "vwap_dist": ((snap['price'] - curr['vwap']) / curr['vwap'] * 100),
        "vwap_status": "强势" if snap['price'] > curr['vwap'] else "弱势",
        "turnover": snap['turnover'], "dist_to_limit": ((upper_limit - snap['price']) / snap['price'] * 100),
        "order_flow": "买盘强" if snap['bid1_vol'] > snap['ask1_vol'] else "卖盘强",
        "sector_pct": sector_pct
    }