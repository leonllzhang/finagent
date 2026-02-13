import baostock as bs
import pandas as pd
import pandas_ta as ta
import sqlite3
import os
import json
import re
from datetime import datetime
from config import Config
from langchain_openai import ChatOpenAI

# 1. 强力直连
os.environ['no_proxy'] = '*'

class ETFLab:
    def __init__(self, db_path="etf_data.db"):
        self.db_path = db_path
        self.init_db()
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            api_key=Config.API_KEY,
            base_url=Config.BASE_URL,
            temperature=0.1
        )

    def init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 定义核心列：symbol, time, open, high, low, close, volume
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etf_history_5min (
                symbol TEXT,
                time TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (symbol, time)
            )
        ''')
        conn.commit()
        conn.close()

    def sync_data(self, symbol, start_date, end_date):
        """同步 BaoStock 数据到本地 SQLite"""
        bs_code = f"sh.{symbol}" if symbol.startswith("5") else f"sz.{symbol}"
        
        print(f"📡 正在从 BaoStock 同步 {symbol} 数据 ({start_date} 至 {end_date})...")
        bs.login()
        
        # 获取 5 分钟线
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,time,open,high,low,close,volume",
            start_date=start_date, 
            end_date=end_date,
            frequency="5", 
            adjustflag="3" 
        )
        
        print(f"BaoStock 状态码: {rs.error_code}, 消息: {rs.error_msg}")
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        bs.logout()

        if not data_list:
            print(f"❌ 未获取到数据。")
            return

        # 转换为 DataFrame
        df = pd.DataFrame(data_list, columns=rs.fields)
        df['symbol'] = symbol
        # 处理时间：将 20260211150000000 转换为 2026-02-11 15:00:00 这种易读格式或保持14位
        df['time'] = df['time'].apply(lambda x: x[:14])
        
        # --- 核心修复点：只筛选数据库中存在的列 ---
        db_columns = ['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']
        df_to_save = df[db_columns].copy() # 丢弃多余的 'date' 列
        
        conn = sqlite3.connect(self.db_path)
        try:
            # 检查去重
            existing_times_df = pd.read_sql(f"SELECT time FROM etf_history_5min WHERE symbol='{symbol}'", conn)
            existing_times = existing_times_df['time'].tolist() if not existing_times_df.empty else []
            
            new_df = df_to_save[~df_to_save['time'].isin(existing_times)]
            
            if not new_df.empty:
                new_df.to_sql('etf_history_5min', conn, if_exists='append', index=False)
                print(f"✅ 成功同步 {len(new_df)} 条记录到数据库。")
            else:
                print("ℹ️ 数据已存在，无需更新。")
        except Exception as e:
            print(f"❌ 数据库操作异常: {e}")
        finally:
            conn.close()

    def load_local_data(self, symbol):
        """从本地数据库读取数据"""
        conn = sqlite3.connect(self.db_path)
        query = f"SELECT * FROM etf_history_5min WHERE symbol = '{symbol}' ORDER BY time ASC"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def run_backtest(self, symbol, sample_count=10):
        """基于本地数据运行 AI 分析"""
        df = self.load_local_data(symbol)
        
        if df.empty or len(df) < 20:
            print(f"❌ 数据库中无 {symbol} 的数据，请先同步。")
            return

        # 1. 计算指标
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        df['MA20'] = ta.sma(df['close'], length=20)
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        df = df.dropna(subset=['RSI', 'MA20'])
        
        # 2. 模拟采样
        test_points = range(0, len(df) - 12, max(1, len(df) // sample_count))
        
        results = []
        for idx in test_points:
            curr = df.iloc[idx]
            
            # 构造 AI 需要的结构
            metrics = {
                "time": curr['time'], "price": curr['close'], "rsi": curr['RSI'],
                "macd_h": curr['MACDh_12_26_9'], "vol_r": curr['vol_ratio'],
                "trend": "多头趋势" if curr['close'] > curr['MA20'] else "空头趋势"
            }

            prompt = f"""
            你是一名高级基金经理。请分析标的 {symbol} 在时刻 {metrics['time']} 的短线机会：
            价格: {metrics['price']}, RSI: {metrics['rsi']:.2f}, MACD柱线: {metrics['macd_h']:.4f}, 量比: {metrics['vol_r']:.2f}, 日线趋势: {metrics['trend']}。
            请给出结论：[买入/卖出/观望] 并给出概率。
            必须在末尾包含此 JSON: SIGNAL_JSON: {{"action": "xxx", "prob": XX}}
            """
            
            try:
                res = self.llm.invoke(prompt)
                ai_text = res.content
                match = re.search(r'SIGNAL_JSON:\s*(\{.*\})', ai_text)
                if match:
                    sig = json.loads(match.group(1))
                    
                    # 验证 1 小时（12个5分钟周期）后表现
                    f_price = df.iloc[idx + 12]['close']
                    profit = ((f_price - curr['close']) / curr['close']) * 100
                    
                    results.append({
                        "时间": metrics['time'], "AI操作": sig['action'], 
                        "AI概率": sig['prob'], "1h后收益%": round(profit, 2)
                    })
                    print(f"[{metrics['time']}] AI建议: {sig['action']} ({sig['prob']}%) -> 实际收益: {profit:.2f}%")
            except Exception as e:
                print(f"分析出错: {e}")

        if results:
            pd.DataFrame(results).to_excel(f"backtest_{symbol}.xlsx", sheet_name= f"result-{datetime.now}", index=False)
            print(f"✅ 回测报告已保存为 backtest_{symbol}.xlsx")

if __name__ == "__main__":
    lab = ETFLab()
    # 步骤 1：同步 (你可以把日期稍微改短一点，比如同步10天)
    # lab.sync_data("510300", "2026-02-01", "2026-02-11")
    # 步骤 2：回测
    lab.run_backtest("510300", sample_count=50)