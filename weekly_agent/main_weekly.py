from weekly_agent.data_manager_bao import WeeklyDataManager
from technical_filter import get_top_candidates
from nodes_weekly import weekly_analyze_node
import pandas as pd
import json, re

def run_weekly_job():
    # 1. 初始化
    dm = WeeklyDataManager("weekly_market.db")
    
    # 【修改点】选择一个确定有数据的交易时段
    # 比如：2026年2月2日（周一）到 2026年2月20日（周五）
    # 或者自动计算：
    from datetime import datetime, timedelta
    end_dt = datetime.now().strftime("%Y-%m-%d")
    start_dt = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
    
    print(f"🕒 自动设定的同步周期: {start_dt} 至 {end_dt}")
    dm.sync_csi300_daily(start_dt, end_dt)

    # 2. 初筛
    candidates = get_top_candidates("weekly_market.db", top_n=30)
    
    if candidates.empty:
        print("⚠️ 初筛结果为空，无法继续分析。请检查：1. 数据库是否有数据；2. 筛选条件是否过严。")
        return

    print(f"🔥 初筛完成，共有 {len(candidates)} 只进入 AI 分析阶段")
    final_results = []

    # 3. AI 深度分析
    for _, stock in candidates.iterrows():
        try:
            print(f"🤖 AI 正在深度评估: {stock['code']}...")
            state = {'current_stock': stock}
            result = weekly_analyze_node(state)
            
            match = re.search(r'WEEKLY_RANKING:\s*(\{.*\})', result['ai_analysis'])
            if match:
                res_json = json.loads(match.group(1))
                # 将初筛的数据也并进去，方便查看
                res_json['weekly_return'] = f"{stock['weekly_return']:.2f}%"
                final_results.append(res_json)
        except Exception as e:
            print(f"❌ 分析 {stock['code']} 时出错: {e}")

    # 4. 生成排行榜并排序
    if final_results:
        rank_df = pd.DataFrame(final_results)
        if 'score' in rank_df.columns:
            rank_df = rank_df.sort_values(by='score', ascending=False)
            rank_df.to_excel("下周潜力个股排行榜.xlsx", index=False)
            print("✨ 排行榜已成功生成：下周潜力个股排行榜.xlsx")
        else:
            print("❌ AI 返回的 JSON 格式不正确，缺少 'score' 字段。")
    else:
        print("❌ 未能生成任何有效分析结果。")

if __name__ == "__main__":
    run_weekly_job()