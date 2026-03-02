import sqlite3
import pandas as pd
import numpy as np

def get_top_candidates(db_path, top_n=30):
    """
    从数据库中筛选出下周最具潜力的股票。
    """
    print("🛠️  正在执行数学初筛 (技术面 + 资金面)...")
    
    conn = sqlite3.connect(db_path)
    try:
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
    
    results = []
    # 2. 遍历每只股票进行指标分析
    for code in df['code'].unique():
        sub = df[df['code'] == code].sort_values('date')
        
        if len(sub) < 5: continue
            
        # A. 动能：累计涨跌幅
        weekly_return = sub['pctChg'].sum() 
        
        # B. 资金：成交量变化 (最近3天均量 vs 之前均量)
        recent_vol_avg = sub['volume'].tail(3).mean()
        prev_vol_avg = sub['volume'].head(len(sub)-3).mean() if len(sub) > 3 else sub['volume'].iloc[0]
        vol_increase = recent_vol_avg / prev_vol_avg if prev_vol_avg > 0 else 1.0
        
        # C. 趋势：MA20 过滤器
        ma20_window = min(20, len(sub))
        ma20 = sub['close'].rolling(window=ma20_window, min_periods=1).mean().iloc[-1]
        is_above_ma20 = sub['close'].iloc[-1] > ma20
        
        # D. 换手率：【核心修复】增加容错处理
        avg_turnover = 0
        if 'turnover' in sub.columns:
            avg_turnover = pd.to_numeric(sub['turnover'], errors='coerce').mean()

        results.append({
            "code": code,
            "weekly_return": round(weekly_return, 2),
            "vol_increase": round(vol_increase, 2),
            "is_above_ma20": is_above_ma20,
            "last_price": sub['close'].iloc[-1],
            "avg_turnover": avg_turnover if not np.isnan(avg_turnover) else 0
        })
    
    if not results: return pd.DataFrame()

    cand_df = pd.DataFrame(results)
    
    # 3. 执行最终过滤：必须在均线之上
    final_candidates = cand_df[cand_df['is_above_ma20'] == True].copy()
    
    # 4. 排序：优先看成交量爆发 (vol_increase)
    final_candidates = final_candidates.sort_values(
        by=['vol_increase', 'weekly_return'], 
        ascending=[False, False]
    )
    
    top_list = final_candidates.head(top_n)
    print(f"✅ 初筛成功！从入库股票中选出 {len(top_list)} 只高动能标的。")
    return top_list