import requests
import pandas as pd
from datetime import datetime
import os
import re

# 强力禁用代理
os.environ['no_proxy'] = '*'

def get_market_prefix(symbol):
    """判定A股市场前缀"""
    if symbol.startswith(('6', '5')):
        return "sh"
    return "sz"

def fetch_batch_performance(codes):
    """
    通过腾讯 API 批量获取最新行情
    """
    if not codes: return pd.DataFrame()
    
    # 格式化代码，腾讯格式为：sh600031,sz000333
    formatted_codes = ",".join([f"{get_market_prefix(c)}{c}" for c in codes])
    url = f"http://qt.gtimg.cn/q={formatted_codes}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # 腾讯返回的是字符串，需要解析
        lines = response.text.strip().split(';')
        
        results = []
        for line in lines:
            if len(line) < 50: continue
            # 正则提取 v_sh600031="xxx" 中的内容
            content = re.search(r'"(.*)"', line).group(1)
            p = content.split('~')
            # 字段索引：1名称, 3当前价, 31昨收, 32涨跌幅
            results.append({
                'code': p[2],
                'name': p[1],
                'today_close': float(p[3]),
                'last_close': float(p[4]),
                'today_change%': float(p[32]),
                'amount_wan': float(p[37]) # 成交额(万元)
            })
        return pd.DataFrame(results)
    except Exception as e:
        print(f"❌ 批量获取行情失败: {e}")
        return pd.DataFrame()

def check_my_rankings(ranking_file="下周潜力个股排行榜.xlsx"):
    """
    检查排行榜中个股的今日表现
    """
    if not os.path.exists(ranking_file):
        print(f"❌ 找不到文件: {ranking_file}")
        return

    # 1. 读取排行榜
    print(f"📖 读取排行榜: {ranking_file} ...")
    df_rank = pd.read_excel(ranking_file)
    
    # 确保代码格式为 6 位字符串
    df_rank['code'] = df_rank['code'].astype(str).str.zfill(6)
    stock_codes = df_rank['code'].tolist()

    # 2. 批量获取今日行情
    print(f"📡 正在获取 {len(stock_codes)} 只个股的腾讯实时快照...")
    df_perf = fetch_batch_performance(stock_codes)
    
    if df_perf.empty:
        print("❌ 无法获取行情数据，程序终止。")
        return

    # 3. 合并数据
    final_df = pd.merge(df_rank, df_perf, on='code', how='left')

    # 4. 计算简单统计
    # 排除今天停牌或者没取到数的情况
    valid_perf = final_df.dropna(subset=['today_change%'])
    avg_chg = valid_perf['today_change%'].mean()
    win_count = len(valid_perf[valid_perf['today_change%'] > 0])
    
    print("\n" + "="*40)
    print(f"📊 今日表现复盘报告 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"🔹 样本总量: {len(valid_perf)} 只")
    print(f"🔹 平均涨跌幅: {avg_chg:.2f}%")
    print(f"🔹 上涨/总数: {win_count} / {len(valid_perf)} (胜率: {win_count/len(valid_perf)*100:.1f}%)")
    print("="*40)

    # 5. 保存结果
    output_name = f"复盘结果_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
    final_df.to_excel(output_name, index=False)
    print(f"✅ 详细复盘报表已保存至: {output_name}")

if __name__ == "__main__":
    check_my_rankings()