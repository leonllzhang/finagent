import efinance as ef
import pandas as pd
import pandas_ta as ta
import os
from datetime import datetime

# 额外强制设置为空
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['all_proxy'] = ''

def fetch_etf_metrics(symbol: str):
    try:
        # 1. 获取历史数据 (多取一点数据以保证长均线计算准确)
        df_history = ef.stock.get_quote_history(symbol)
        if df_history is None or df_history.empty:
            raise ValueError(f"无法获取代码 {symbol} 的历史数据")

        # 映射列名
        column_mapping = {'开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume'}
        df_history = df_history.rename(columns=column_mapping)
        for col in ['open', 'close', 'high', 'low', 'volume']:
            df_history[col] = pd.to_numeric(df_history[col], errors='coerce')

        # 2. 计算高级指标
        # 短期均线 MA20 (月线级别趋势)
        df_history['MA20'] = ta.sma(df_history['close'], length=20)
        # 中期均线 MA60 (季度线级别/牛熊分界)
        df_history['MA60'] = ta.sma(df_history['close'], length=60)
        # RSI 与 MACD
        df_history['RSI'] = ta.rsi(df_history['close'], length=14)
        macd = ta.macd(df_history['close'])
        df_history = pd.concat([df_history, macd], axis=1)
        
        # 3. 计算量比 (当前成交量 vs 过去5日平均成交量)
        avg_volume_5d = df_history['volume'].tail(6).head(5).mean()
        current_volume = df_history['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume_5d if avg_volume_5d != 0 else 1

        latest = df_history.iloc[-1]

        # 4. 获取实时快照
        df_spot = ef.stock.get_base_info(symbol)
        spot_data = df_spot.iloc[0].to_dict() if isinstance(df_spot, pd.DataFrame) else df_spot.to_dict()

        # 自动获取名称和涨跌幅
        name = next((v for k, v in spot_data.items() if '名称' in str(k)), "未知")
        pct_chg = next((v for k, v in spot_data.items() if '涨跌幅' in str(k)), 0)

        return {
            "name": name,
            "current_price": latest['close'],
            "pct_change": pct_chg,
            "rsi": latest['RSI'],
            "ma20": latest['MA20'],
            "ma60": latest['MA60'],
            "volume_ratio": volume_ratio,
            "macd_line": latest['MACD_12_26_9'],
            "macd_signal": latest['MACDs_12_26_9'],
            "macd_hist": latest['MACDh_12_26_9'],
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_market_closing": 14 <= datetime.now().hour < 15 # 是否接近收盘
        }
    except Exception as e:
        print(f"采集层报错: {e}")
        raise e