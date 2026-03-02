import pandas as pd
import sqlite3
import requests
import baostock as bs
import time, os, re, json

class WeeklyDataManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }

    def sync_csi300_daily(self, start_date, end_date):
        print("📡 正在获取沪深300成分股名单...")
        bs.login()
        stocks = []
        rs = bs.query_hs300_stocks()
        while rs.next():
            stocks.append(rs.get_row_data()[1].split('.')[-1])
        bs.logout()
        print(f"✅ 成功获取 {len(stocks)} 只代码")

        conn = sqlite3.connect(self.db_path)
        conn.execute("DROP TABLE IF EXISTS daily_hists")
        # 统一表结构，增加 turnover
        conn.execute('''
            CREATE TABLE daily_hists (
                date TEXT, code TEXT, open REAL, high REAL, low REAL, 
                close REAL, volume REAL, pctChg REAL, turnover REAL
            )
        ''')
        conn.commit()
        
        print(f"📡 正在通过新浪财经抓取价格数据...")
        success = 0
        for i, code in enumerate(stocks):
            try:
                prefix = "sh" if code.startswith(('6', '5')) else "sz"
                url = f"https://quotes.sina.cn/cn/api/jsonp.php/_/CN_MarketDataService.getKLineData?symbol={prefix}{code}&scale=240&ma=no&datalen=20"
                res = requests.get(url, timeout=10)
                match = re.search(r'\[.*\]', res.text)
                if not match: continue
                df = pd.DataFrame(json.loads(match.group()))
                if not df.empty:
                    df['pctChg'] = df['close'].astype(float).pct_change() * 100
                    df['code'] = code
                    df['turnover'] = 0  # 新浪接口无换手率，填充0
                    df.rename(columns={'day': 'date'}, inplace=True)
                    # 过滤日期
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                    if not df.empty:
                        df[['date','code','open','high','low','close','volume','pctChg','turnover']].to_sql(
                            'daily_hists', conn, if_exists='append', index=False
                        )
                        success += 1
                if (i + 1) % 50 == 0: print(f"进度: {i + 1}/300...")
                time.sleep(0.05)
            except: continue
        conn.close()
        print(f"✅ 同步完成！共入库 {success} 只股票交易数据。")