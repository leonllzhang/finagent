import pandas as pd
import sqlite3
import efinance as ef
import baostock as bs
import time
import os

class WeeklyDataManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def sync_csi300_daily(self, start_date, end_date):
        """混合模式：BaoStock取名单 + efinance取数据"""
        
        # 1. 使用 BaoStock 获取沪深 300 成分股代码
        print("📡 正在获取沪深300成分股名单...")
        bs.login()
        rs = bs.query_hs300_stocks()
        stocks = []
        while rs.next():
            stocks.append(rs.get_row_data())
        bs.logout()
        
        if not stocks:
            print("❌ 无法获取成分股名单，请检查网络")
            return
            
        # 提取 6 位数字代码 (例如 sh.600000 -> 600000)
        stock_list = [s[1].split('.')[-1] for s in stocks]
        print(f"✅ 成功获取 {len(stock_list)} 只成分股代码")

        # 2. 初始化数据库
        conn = sqlite3.connect(self.db_path)
        conn.execute("DROP TABLE IF EXISTS daily_hists")
        conn.execute('''
            CREATE TABLE daily_hists (
                date TEXT, code TEXT, open REAL, high REAL, low REAL, 
                close REAL, volume REAL, amount REAL, pctChg REAL, turnover REAL
            )
        ''')
        conn.commit()
        
        # 3. 通过 efinance 抓取历史
        print(f"📡 正在抓取数据 ({start_date} ~ {end_date})...")
        beg = start_date.replace('-', '')
        end = end_date.replace('-', '')

        success_count = 0
        for i, code in enumerate(stock_list):
            try:
                # 获取该代码的历史日线
                df = ef.stock.get_quote_history(code, beg=beg, end=end)
                if not df.empty:
                    # 映射 efinance 到数据库列名
                    df_to_save = pd.DataFrame()
                    df_to_save['date'] = df['日期']
                    df_to_save['code'] = df['股票代码']
                    df_to_save['open'] = df['开盘']
                    df_to_save['high'] = df['最高']
                    df_to_save['low'] = df['最低']
                    df_to_save['close'] = df['收盘']
                    df_to_save['volume'] = df['成交量']
                    df_to_save['amount'] = df['成交额']
                    df_to_save['pctChg'] = df['涨跌幅']
                    df_to_save['turnover'] = df['换手率']
                    
                    df_to_save.to_sql('daily_hists', conn, if_exists='append', index=False)
                    success_count += 1
                
                # 每 50 只打印一次进度
                if (i + 1) % 50 == 0:
                    print(f"已完成 {i + 1} 只...")
            except Exception as e:
                # 遇到个别错误跳过，不影响整体
                continue
        
        conn.close()
        print(f"✅ 同步完成！成功入库 {success_count} 只股票的交易数据。")