import baostock as bs
import pandas as pd
import datetime

class WeeklyDataScanner:
    def __init__(self):
        bs.login()

    def get_csi300_list(self):
        """获取沪深300成分股"""
        rs = bs.query_hs300_stocks()
        stocks = []
        while rs.next():
            stocks.append(rs.get_row_data())
        return pd.DataFrame(stocks, columns=rs.fields)

    def fetch_weekly_technicals(self, symbol):
        """获取单只股票上一周的汇总数据"""
        # 自动转换代码格式
        code = f"sh.{symbol}" if symbol.startswith('6') else f"sz.{symbol}"
        
        # 获取最近两周的数据来计算变化
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=20)).strftime("%Y-%m-%d")
        
        rs = bs.query_history_k_data_plus(code,
            "date,code,open,high,low,close,volume,amount,pctChg",
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag="3")
        
        data_list = []
        while rs.next(): data_list.append(rs.get_row_data())
        df = pd.DataFrame(data_list, columns=rs.fields)
        if df.empty: return None
        
        # 计算上一周的指标
        df['close'] = pd.to_numeric(df['close'])
        avg_price = df['close'].mean()
        total_pct = df['pctChg'].astype(float).sum()
        vol_std = df['volume'].astype(float).std() # 波动率指标
        
        return {
            "last_week_avg": round(avg_price, 2),
            "weekly_return": f"{total_pct:.2f}%",
            "current_price": df['close'].iloc[-1],
            "volatility": "高" if vol_std > df['volume'].astype(float).mean()*0.5 else "平稳"
        }

    def fetch_stock_news_sentiment(self, symbol):
        """
        模拟新闻抓取（实际可用爬虫或新闻API）
        这里暂用模拟结论，实际可对接新浪/财联社
        """
        # 演示用：实际开发中这里会接入 requests 爬取
        return "行业利好传闻，主力资金周五小幅流出，机构评级上调。"