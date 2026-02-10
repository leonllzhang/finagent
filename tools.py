import requests
import pandas as pd
import pandas_ta as ta
import os
import re
import json

# 强力禁用代理
os.environ['no_proxy'] = '*'

def fetch_etf_metrics_5min(symbol: str):
    """
    通过新浪财经接口获取 5 分钟 K 线数据
    symbol: 510300, 513100 等
    """
    try:
        # 1. 自动转换代码格式 (新浪格式: sh510300, sz159941)
        market = "sh" if symbol.startswith("5") else "sz"
        full_symbol = f"{market}{symbol}"
        
        # 新浪 5 分钟 K 线接口
        # scale=5 表示 5 分钟, datalen=100 表示取 100 条
        url = f"https://quotes.sina.cn/cn/api/jsonp.php/var_{full_symbol}_5/CN_MarketDataService.getKLineData?symbol={full_symbol}&scale=5&ma=no&datalen=100"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        text = response.text
        
        # 2. 解析新浪特有的 JSONP 格式
        # 新浪返回的是 var_sh510300_5_xxx=[{...},{...}]; 这种字符串
        # 我们需要用正则提取中括号里的内容
        match = re.search(r'\[.*\]', text)
        if not match:
            raise ValueError(f"新浪接口返回格式错误或无数据: {text[:100]}")
            
        data_json = match.group()
        raw_data = json.loads(data_json)
        
        # 3. 转化为 DataFrame
        # 新浪列名: day (时间), open, high, low, close, volume
        df = pd.DataFrame(raw_data)
        
        # 转换数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])

        # 4. 计算指标 (正序)
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        
        # 计算量比 (当前5分钟量 / 过去20个5分钟均量)
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()

        # 5. 提取当前和上一条
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # 6. 获取名称 (使用腾讯的快照接口获取名称，这个接口很稳)
        name = symbol
        try:
            name_url = f"http://qt.gtimg.cn/q={full_symbol}"
            name_res = requests.get(name_url, timeout=5).text
            if '~' in name_res:
                name = name_res.split('~')[1]
        except:
            pass

        return {
            "name": name,
            "time": curr['day'],
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
        print(f"❌ 数据采集报错: {e}")
        raise e