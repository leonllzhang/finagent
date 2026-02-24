import efinance as ef
import pandas as pd

def verify_rankings(excel_file):
    # 1. 加载你之前的排行榜
    df_rank = pd.read_excel(excel_file)
    
    results = []
    print(f"📊 正在验证 {len(df_rank)} 只个股的下周表现...")

    for _, row in df_rank.iterrows():
        code = str(row['code'])
        # 2. 获取该股下周的数据 (假设验证日是下周五)
        # 这里的 beg 和 end 设为下周一到下周五
        df_next_week = ef.stock.get_quote_history(code, beg='20260302', end='20260306')
        
        if not df_next_week.empty:
            open_price = df_next_week['开盘'].iloc[0]  # 周一开盘价
            close_price = df_next_week['收盘'].iloc[-1] # 周五收盘价
            actual_return = ((close_price - open_price) / open_price) * 100
            
            results.append({
                "代码": code,
                "AI评分": row['score'],
                "周收益%": round(actual_return, 2),
                "是否盈利": "✅" if actual_return > 0 else "❌"
            })

    # 3. 统计胜率
    v_df = pd.DataFrame(results)
    win_rate = (v_df['周收益%'] > 0).mean()
    avg_return = v_df['周收益%'].mean()
    
    print(f"\n--- 验证总结 ---")
    print(f"🔹 总体胜率: {win_rate*100:.2f}%")
    print(f"🔹 平均收益: {avg_return:.2f}%")
    # 查看高分股(>85)的表现
    high_score_win_rate = (v_df[v_df['AI评分'] > 85]['周收益%'] > 0).mean()
    print(f"🔹 高分股(>85分)胜率: {high_score_win_rate*100:.2f}%")