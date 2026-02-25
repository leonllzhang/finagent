import requests
import pandas as pd
import re
import json
from datetime import datetime, timedelta
import os

# 强力净化环境，禁用代理
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]
os.environ['no_proxy'] = '*'

class SinaFinanceStableAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }

    def get_market_prefix(self, symbol):
        if symbol.startswith(('6', '5', '000300')): return "sh"
        return "sz"

    def get_daily_hists(self, symbol, datalen=20):
        """
        获取日线数据 (使用新浪最稳接口)
        """
        prefix = self.get_market_prefix(symbol)
        full_symbol = f"{prefix}{symbol}"
        url = f"https://quotes.sina.cn/cn/api/jsonp.php/_/CN_MarketDataService.getKLineData?symbol={full_symbol}&scale=240&ma=no&datalen={datalen}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            # 提取 JSON 数组
            match = re.search(r'\[.*\]', resp.text)
            if not match: return pd.DataFrame()
            
            df = pd.DataFrame(json.loads(match.group()))
            if df.empty: return df
            
            # 统一字段名与类型
            # 字段含义：day:日期, open, high, low, close, volume:量(股)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 修复新浪成交额缺失：估算成交额(万元) = (成交量/100) * 均价 / 10000
            # A股成交量通常为股，这里转为万元
            df['amount_wan'] = (df['volume'] * (df['open'] + df['close']) / 2) / 10000
            return df
        except Exception as e:
            print(f"DEBUG: 获取 {symbol} 失败 -> {e}")
            return pd.DataFrame()

    def get_realtime_snapshot(self, codes):
        """腾讯快照接口补全最新数据"""
        if not codes: return {}
        formatted = ",".join([f"{self.get_market_prefix(c)}{c}" for c in codes])
        url = f"http://qt.gtimg.cn/q={formatted}"
        try:
            res = requests.get(url, timeout=10).text
            results = {}
            for line in res.strip().split(';'):
                if len(line) < 50: continue
                p = re.search(r'"(.*)"', line).group(1).split('~')
                # p[2]:代码, p[3]:现价, p[32]:涨跌%, p[37]:成交额(万), p[38]:换手%
                results[p[2]] = {
                    'price': float(p[3]),
                    'chg%': float(p[32]),
                    'amt_wan': float(p[37]),
                    'turnover%': float(p[38]) if p[38] else 0
                }
            return results
        except: return {}

def run_pro_review(ranking_file="下周潜力个股排行榜.xlsx"):
    if not os.path.exists(ranking_file):
        print(f"❌ 找不到文件: {ranking_file}")
        return

    api = SinaFinanceStableAPI()
    
    # 1. 确定本周交易日历
    print("📅 正在确定本周交易日历...")
    df_idx = api.get_daily_hists("000300")
    if df_idx.empty:
        print("❌ 无法从接口获取行情，请检查网络连接")
        return
    
    # 找到本周一的日期
    now = datetime.now()
    monday_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
    this_week_df = df_idx[df_idx['day'] >= monday_date].sort_values('day')
    
    if this_week_df.empty:
        # 如果还没数据，取最新一天作为起始
        week_days = [df_idx.iloc[-1]['day']]
        idx_open = float(df_idx.iloc[-1]['open'])
    else:
        week_days = this_week_df['day'].tolist()
        idx_open = float(this_week_df.iloc[0]['open'])

    # 2. 读取排行榜
    df_rank = pd.read_excel(ranking_file)
    df_rank['code'] = df_rank['code'].astype(str).str.zfill(6)
    name_col = next((c for c in df_rank.columns if any(k in c.lower() for k in ['名', 'name', '股票'])), 'code')
    codes = df_rank['code'].tolist()

    print(f"📡 监测周期: {week_days[0]} 至 {week_days[-1]}")
    print(f"📡 正在拉取 {len(codes)} 只个股全维度数据...")
    
    rt_snapshots = api.get_realtime_snapshot(codes)
    final_list = []

    for _, row in df_rank.iterrows():
        code = row['code']
        df_h = api.get_daily_hists(code)
        if df_h.empty: continue
        
        # 定位基准：本周首个交易日的开盘价
        stock_week = df_h[df_h['day'] >= week_days[0]].sort_values('day')
        if stock_week.empty: continue
        mon_open = stock_week.iloc[0]['open']
        
        res = row.to_dict()
        current_close = 0
        
        # 逐日填充
        for day in week_days:
            day_match = df_h[df_h['day'] == day]
            if not day_match.empty:
                idx = day_match.index[0]
                close_p = day_match.iloc[0]['close']
                amt_wan = day_match.iloc[0]['amount_wan']
                current_close = close_p
                
                # 写入每日列
                res[f"{day[5:]} 收盘"] = close_p
                res[f"{day[5:]} 额(万)"] = round(amt_wan, 2)
                if idx > 0:
                    prev_c = df_h.iloc[idx-1]['close']
                    res[f"{day[5:]} (%)"] = round(((close_p - prev_c) / prev_c) * 100, 2)

        # 补全实时最新指标
        rt = rt_snapshots.get(code, {})
        if rt:
            res['当前价'] = rt['price']
            res['今日换手%'] = rt['turnover%']
            # 如果历史数据没跟上，用实时成交额补全今天
            today_short = week_days[-1][5:]
            if f"{today_short} 额(万)" not in res or res[f"{today_short} 额(万)"] == 0:
                res[f"{today_short} 额(万)"] = rt['amt_wan']
            
            # 计算累计收益
            wtd_ret = ((rt['price'] - mon_open) / mon_open) * 100
            res['本周累计%'] = round(wtd_ret, 2)
            
            # 计算大盘基准收益 (腾讯快照查实时大盘)
            try:
                idx_rt = float(requests.get("http://qt.gtimg.cn/q=sh000300").text.split('~')[3])
                idx_wtd = ((idx_rt - idx_open) / idx_open) * 100
                res['超额收益%'] = round(wtd_ret - idx_wtd, 2)
            except:
                res['超额收益%'] = 0

        final_list.append(res)

    if not final_list:
        print("❌ 未能匹配到有效的个股数据")
        return

    # 结果处理
    report_df = pd.DataFrame(final_list)
    avg_alpha = report_df['超额收益%'].mean() if '超额收益%' in report_df.columns else 0

    print("\n" + " 潜力股旗舰复盘看板 ".center(50, "="))
    print(f"📊 周期: {week_days[0]} -> {week_days[-1]}")
    print(f"🔹 组合平均累计: {report_df['本周累计%'].mean():.2f}%")
    print(f"🔥 平均超额 Alpha: {avg_alpha:.2f}%")
    print(f"📈 跑赢大盘个股: {len(report_df[report_df['超额收益%'] > 0])} / {len(report_df)}")
    print("="*55)

    # 导出
    output = f"全维度复盘_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
    all_cols = report_df.columns.tolist()
    header_cols = [c for c in ['code', name_col, 'score', '本周累计%', '超额收益%', '今日换手%'] if c in all_cols]
    daily_cols = sorted([c for c in all_cols if '-' in c], reverse=False)
    other_cols = [c for c in all_cols if c not in header_cols and c not in daily_cols]
    
    report_df[header_cols + daily_cols + other_cols].sort_values(by='score', ascending=False).to_excel(output, index=False)
    print(f"✨ 旗舰复盘表已生成: {output}")

if __name__ == "__main__":
    run_pro_review()