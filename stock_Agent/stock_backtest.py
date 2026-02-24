import baostock as bs
import pandas as pd
import pandas_ta as ta
import sqlite3
import os
import json
import re
import time
from datetime import datetime
from config_stock import StockConfig  # 导入配置类
from langchain_openai import ChatOpenAI

# 1. 环境净化
os.environ['no_proxy'] = '*'

class StockBacktester:
    def __init__(self, db_path="stock_data.db"):
        self.db_path = db_path
        self.init_db()
        self.llm = ChatOpenAI(
            model=StockConfig.MODEL_NAME,
            api_key=StockConfig.API_KEY,
            base_url=StockConfig.BASE_URL,
            temperature=0.1
        )

    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS stock_history_5min 
                     (symbol TEXT, time TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL, amount REAL, PRIMARY KEY (symbol, time))''')
        conn.close()

    def sync_data(self, symbol, start_date, end_date):
        """同步数据逻辑"""
        # 自动转换 BaoStock 格式 (sh.600031 / sz.000333)
        prefix = "sh." if symbol.startswith(('6', '5')) else "sz."
        bs_code = f"{prefix}{symbol}"
        
        bs.login()
        # 获取 5 分钟线
        rs = bs.query_history_k_data_plus(
            bs_code, "date,time,open,high,low,close,volume,amount",
            start_date=start_date, end_date=end_date,
            frequency="5", adjustflag="3"
        )
        
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        
        if not data:
            print(f"⚠️ {symbol} 未获取到数据，请检查日期或代码。")
            return

        df = pd.DataFrame(data, columns=rs.fields)
        df['symbol'] = symbol
        df['time'] = df['time'].apply(lambda x: x[:14])
        
        # 写入数据库 (忽略重复主键)
        conn = sqlite3.connect(self.db_path)
        try:
            # 这里的逻辑是只插入不重复的时间点
            existing = pd.read_sql(f"SELECT time FROM stock_history_5min WHERE symbol='{symbol}'", conn)['time'].tolist()
            new_df = df[~df['time'].isin(existing)]
            if not new_df.empty:
                new_df[['symbol','time','open','high','low','close','volume','amount']].to_sql(
                    'stock_history_5min', conn, if_exists='append', index=False
                )
        except Exception as e:
            print(f"写入 {symbol} 失败: {e}")
        finally:
            conn.close()

    def load_data(self, symbol):
        """从本地加载数据"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql(f"SELECT * FROM stock_history_5min WHERE symbol='{symbol}' ORDER BY time ASC", conn)
        conn.close()
        if df.empty: return df
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def prepare_indicators(self, df):
        """指标预计算"""
        df['date_only'] = df['time'].str[:8]
        # VWAP
        df['tp'] = (df['high'] + df['low'] + df['close']) / 3
        df['pv'] = df['tp'] * df['volume']
        df['vwap'] = df.groupby('date_only')['pv'].cumsum() / df.groupby('date_only')['volume'].cumsum()
        # RSI & MACD
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        # 获取 MACD 柱状图列名并计算斜率
        hist_col = [c for c in df.columns if 'MACDh' in c][0]
        df['macd_slope'] = df[hist_col].diff()
        # Bollinger
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        # 量比
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(20, min_periods=1).mean()
        return df, hist_col

    def run_backtest_all(self, start_date, end_date, sample_per_stock=10):
        """批量运行配置列表中的所有个股回测"""
        print(f"🧪 开始批量回测工程...")
        
        all_summary = []

        for item in StockConfig.MONITOR_LIST:
            stock = item['symbol']
            sector = item['sector']
            
            print(f"\n--- 正在处理 {stock} (行业参考: {sector}) ---")
            
            # 1. 同步数据 (可选：如果数据库已有可跳过)
            self.sync_data(stock, start_date, end_date)
            self.sync_data(sector, start_date, end_date)
            
            # 2. 加载数据
            s_df = self.load_data(stock)
            sec_df = self.load_data(sector)
            
            if s_df.empty or sec_df.empty:
                print(f"跳过 {stock}: 数据不足")
                continue

            # 3. 计算指标
            s_df, hist_col_name = self.prepare_indicators(s_df)
            s_df = s_df.dropna().reset_index(drop=True)
            
            # 4. 采样分析
            step = max(1, len(s_df) // sample_per_stock)
            stock_results = []
            
            for idx in range(0, len(s_df) - 12, step):
                curr = s_df.iloc[idx]
                
                # 获取板块同步涨跌幅
                try:
                    sec_now = sec_df[sec_df['time'] <= curr['time']].iloc[-1]
                    sec_prev = sec_df[sec_df['time'] < curr['time']].iloc[-1]
                    sector_pct = ((sec_now['close'] - sec_prev['close']) / sec_prev['close']) * 100
                except:
                    sector_pct = 0

                # 模拟当时环境的 Prompt
                prompt = f"""
                你是量化分析师。分析 {stock} 在 {curr['time']} 的表现：
                现价:{curr['close']}, VWAP:{curr['vwap']:.2f}, RSI:{curr['RSI']:.2f}, 
                MACD斜率:{curr['macd_slope']:.4f}, 量比:{curr['vol_ratio']:.2f},
                板块涨跌:{sector_pct:.2f}%, 趋势:{"多头" if curr['close'] > curr['vwap'] else "空头"}。
                请给出建议并包含 SIGNAL_JSON: {{"action": "买入/卖出/观望", "probability": XX}}
                """
                
                try:
                    res = self.llm.invoke(prompt)
                    match = re.search(r'SIGNAL_JSON:\s*(\{.*\})', res.content)
                    if match:
                        sig = json.loads(match.group(1))
                        # 结果校验：1小时后收益
                        future_p = s_df.iloc[idx + 12]['close']
                        profit = ((future_p - curr['close']) / curr['close']) * 100
                        
                        stock_results.append({
                            "股票": stock, "时间": curr['time'], "建议": sig['action'],
                            "置信度": sig['probability'], "1h后收益%": round(profit, 2)
                        })
                except Exception as e:
                    print(f"AI分析失败 {stock} @ {curr['time']}: {e}")

            # 导出个股结果
            if stock_results:
                res_df = pd.DataFrame(stock_results)
                res_df.to_excel(f"backtest_res_{stock}.xlsx", index=False)
                all_summary.extend(stock_results)
                print(f"✅ {stock} 回测完成，样本数: {len(stock_results)}")

        # 导出总汇总结果
        if all_summary:
            summary_df = pd.DataFrame(all_summary)
            summary_df.to_excel("backtest_summary_all.xlsx", index=False)
            print(f"\n✨ 批量回测结束！总报告: backtest_summary_all.xlsx")

if __name__ == "__main__":
    tester = StockBacktester()
    
    # 执行参数
    TEST_START = "2026-02-01"
    TEST_END = "2026-02-23"
    SAMPLE_POINTS = 5 # 每只股票随机测试 5 个点位（防止 API Token 消耗过大）

    tester.run_backtest_all(TEST_START, TEST_END, sample_per_stock=SAMPLE_POINTS)