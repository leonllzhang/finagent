import os
from datetime import datetime, timedelta
import pandas as pd
import json, re

from data_manager import WeeklyDataManager
from technical_filter import get_top_candidates
from news_manager import NewsManager
from nodes_weekly import market_sentiment_node, weekly_analyze_node

def run_weekly_job():
    os.environ['no_proxy'] = '*'
    
    # 1. 数据同步（使用新浪稳定接口）
    dm = WeeklyDataManager("weekly_market.db")
    end_dt = datetime.now().strftime("%Y-%m-%d")
    start_dt = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
    dm.sync_csi300_daily(start_dt, end_dt) 

    # 2. 抓取新闻并分析情绪
    macro_text = NewsManager.get_macro_news(top_n=30)
    sentiment_result = market_sentiment_node({"macro_news": macro_text})
    sentiment_data = sentiment_result['sentiment_analysis']
    print(f"🌍 避险系数: {sentiment_data['risk_score']} | 风险点: {sentiment_data['theme']}")

    # 3. 数学初筛
    candidates = get_top_candidates("weekly_market.db", top_n=30)
    if candidates.empty: return

    final_results = []
    # 4. AI 逐一深度评估
    for _, stock in candidates.iterrows():
        try:
            print(f"🤖 评估 {stock['code']}...")
            res = weekly_analyze_node({'current_stock': stock, 'sentiment_analysis': sentiment_data})
            match = re.search(r'WEEKLY_RANKING:\s*(\{.*\})', res['ai_analysis'])
            if match:
                item = json.loads(match.group(1))
                item['weekly_return'] = f"{stock['weekly_return']:.2f}%"
                final_results.append(item)
        except Exception as e: continue

    # 5. 生成排行榜
    if final_results:
        rank_df = pd.DataFrame(final_results).sort_values(by='score', ascending=False)
        output = f"地缘风控选股榜_{datetime.now().strftime('%m%d')}.xlsx"
        rank_df.to_excel(output, index=False)
        print(f"✨ 报告已生成: {output}")

if __name__ == "__main__":
    run_weekly_job()