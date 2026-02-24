import baostock as bs
import pandas as pd
import sqlite3
import time

class WeeklyDataManager:
    def __init__(self, db_path):
        self.db_path = db_path
        bs.login()

    def sync_csi300_daily(self, start_date, end_date):
        # 1. 获取最新的沪深300名单
        rs = bs.query_hs300_stocks()
        stocks = []
        while rs.next():
            stocks.append(rs.get_row_data())
        
        if not stocks:
            print("❌ 无法获取沪深300成分股名单")
            return
            
        df_stocks = pd.DataFrame(stocks, columns=rs.fields)

        # 2. 预先建立数据库表结构 (无论有没有数据，表必须存在)
        conn = sqlite3.connect(self.db_path)
        conn.execute("DROP TABLE IF EXISTS daily_hists")
        conn.execute('''
            CREATE TABLE daily_hists (
                date TEXT, code TEXT, open REAL, high REAL, low REAL, 
                close REAL, volume REAL, amount REAL, pctChg REAL, turnover REAL
            )
        ''')
        conn.commit()
        
        print(f"📡 正在抓取数据 ({start_date} ~ {end_date})...")
        
        success_count = 0
        # 为了测试，可以先取前 50 只，成功后再全量
        for index, row in df_stocks.iterrows():
            code = row['code']
            rs_data = bs.query_history_k_data_plus(
                code,
                "date,code,open,high,low,close,volume,amount,pctChg,turnover",
                start_date=start_date, end_date=end_date, 
                frequency="d", adjustflag="3"
            )
            
            data = []
            while rs_data.next():
                data.append(rs_data.get_row_data())
            
            if data:
                df = pd.DataFrame(data, columns=rs_data.fields)
                df.to_sql('daily_hists', conn, if_exists='append', index=False)
                success_count += 1
            
            # 打印前 5 只的抓取情况用于调试
            if index < 5:
                print(f"检查 {code}: {'成功' if data else '无数据'}")

            # 关键：每抓取 10 只休眠一下，防止被封
            if index % 10 == 0:
                time.sleep(0.2)
        
        conn.close()
        print(f"✅ 同步任务结束，有效股票数: {success_count}")