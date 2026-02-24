import sqlite3
import pandas as pd
import numpy as np

def get_top_candidates(db_path, top_n=30):
    """
    从数据库中筛选出下周最具潜力的股票。
    筛选逻辑：
    1. 趋势：收盘价必须在 MA20 均线之上。
    2. 动能：区间累计涨幅较好。
    3. 资金：成交量有明显的脉冲放大（量增价稳/量增价升）。
    """
    print("🛠️  正在执行数学初筛 (技术面 + 资金面)...")
    
    conn = sqlite3.connect(db_path)
    try:
        # 读取所有日线历史
        df = pd.read_sql("SELECT * FROM daily_hists", conn)
    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

    if df.empty:
        print("⚠️ 数据库为空，无法筛选。")
        return pd.DataFrame()

    # 1. 数据类型转换
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['pctChg'] = pd.to_numeric(df['pctChg'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df = df.dropna(subset=['close', 'pctChg', 'volume'])
    
    results = []
    # 2. 遍历每只股票进行指标分析
    for code in df['code'].unique():
        # 获取单只股票数据并按时间排序
        sub = df[df['code'] == code].sort_values('date')
        
        # 数据太少（少于 5 天）不参与筛选
        if len(sub) < 5:
            continue
            
        # --- A. 动能：累计涨跌幅 ---
        # efinance 的 pctChg 是 1.5 代表 1.5%
        weekly_return = sub['pctChg'].sum() 
        
        # --- B. 资金：成交量变化 ---
        # 计算最近 3 天的均量 vs 之前几天的均量（量能爆发比）
        recent_vol_avg = sub['volume'].tail(3).mean()
        prev_vol_avg = sub['volume'].head(len(sub)-3).mean() if len(sub) > 3 else sub['volume'].iloc[0]
        
        # 防止除以 0
        vol_increase = recent_vol_avg / prev_vol_avg if prev_vol_avg > 0 else 1.0
        
        # --- C. 趋势：MA20 过滤器 ---
        # 如果数据量不足 20 天，使用所有数据的平均值作为参考
        ma20_window = min(20, len(sub))
        ma20 = sub['close'].rolling(window=ma20_window, min_periods=1).mean().iloc[-1]
        is_above_ma20 = sub['close'].iloc[-1] > ma20
        
        # --- D. 换手率：是否有活跃度 ---
        avg_turnover = pd.to_numeric(sub['turnover'], errors='coerce').mean()

        results.append({
            "code": code,
            "weekly_return": round(weekly_return, 2),
            "vol_increase": round(vol_increase, 2),
            "is_above_ma20": is_above_ma20,
            "last_price": sub['close'].iloc[-1],
            "avg_turnover": avg_turnover
        })
    
    if not results:
        return pd.DataFrame()

    cand_df = pd.DataFrame(results)
    
    # 3. 执行最终过滤
    # 必须在均线之上 (趋势项)
    final_candidates = cand_df[cand_df['is_above_ma20'] == True].copy()
    
    # 4. 排序权重分配
    # 我们认为成交量突然放大 (vol_increase) 是个股起飞的最重要前兆
    # 其次是价格已经展现出来的动能 (weekly_return)
    final_candidates = final_candidates.sort_values(
        by=['vol_increase', 'weekly_return'], 
        ascending=[False, False]
    )
    
    # 5. 返回前 N 名
    top_list = final_candidates.head(top_n)
    
    print(f"✅ 初筛成功！从 300 只中选出 {len(top_list)} 只高动能标的。")
    return top_list