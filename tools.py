import efinance as ef
import pandas as pd
import pandas_ta as ta
import os

# 彻底禁用代理
os.environ['no_proxy'] = '*'

def fetch_etf_metrics(symbol: str):
    """
    使用 efinance 获取数据，并自动适配列名
    """
    try:
        print(f"DEBUG: 正在获取 {symbol} 的历史数据...")
        # 1. 获取历史 K 线
        df_history = ef.stock.get_quote_history(symbol)
        if df_history is None or df_history.empty:
            raise ValueError(f"无法获取代码 {symbol} 的历史数据")

        # 映射列名计算指标
        df_history = df_history.tail(60).copy()
        column_mapping = {'开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume'}
        df_history = df_history.rename(columns=column_mapping)
        
        for col in ['open', 'close', 'high', 'low']:
            df_history[col] = pd.to_numeric(df_history[col], errors='coerce')

        # 计算指标
        df_history['RSI'] = ta.rsi(df_history['close'], length=14)
        macd = ta.macd(df_history['close'])
        df_history = pd.concat([df_history, macd], axis=1)
        latest_history = df_history.iloc[-1]

        # 2. 获取实时快照
        print(f"DEBUG: 正在获取 {symbol} 的实时快照...")
        df_spot = ef.stock.get_base_info(symbol)
        
        # 将 DataFrame 转为字典，方便查找
        if isinstance(df_spot, pd.DataFrame):
            spot_data = df_spot.iloc[0].to_dict()
        else:
            spot_data = df_spot.to_dict()

        # --- 核心逻辑：自动探测列名 ---
        def get_value_by_keyword(data_dict, keyword, fallback_value=0):
            """在字典中找包含关键字的 key，并返回数值"""
            for k, v in data_dict.items():
                if keyword in str(k):
                    return v
            return fallback_value

        # 尝试从快照中找，找不到就从历史 K 线里拿
        name = get_value_by_keyword(spot_data, '名称', '未知ETF')
        price = get_value_by_keyword(spot_data, '价', latest_history['close'])
        change = get_value_by_keyword(spot_data, '涨跌幅', 0)

        print(f"✅ 成功采集: {name} | 当前价: {price} | RSI: {latest_history['RSI']:.2f}")

        return {
            "name": name,
            "current_price": price,
            "pct_change": change,
            "rsi": latest_history['RSI'],
            "macd_line": latest_history['MACD_12_26_9'],
            "macd_signal": latest_history['MACDs_12_26_9'],
            "macd_hist": latest_history['MACDh_12_26_9']
        }

    except Exception as e:
        print(f"❌ 采集层报错: {e}")
        # 如果报错，打印一下到底返回了什么列名，方便调试
        if 'df_spot' in locals():
            print(f"DEBUG: 接口返回的列名有: {df_spot.columns.tolist() if hasattr(df_spot, 'columns') else '无'}")
        raise e