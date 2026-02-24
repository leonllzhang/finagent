import time, os, re, json
from datetime import datetime
from graph_stock import create_graph
from config_stock import StockConfig

def run_monitor():
    os.environ['no_proxy'] = '*'
    agent = create_graph()
    print(f"🚀 个股量化监控雷达启动 | 目标: {[s['symbol'] for s in StockConfig.MONITOR_LIST]}")

    while True:
        now = datetime.now()
        now_time = (now.hour, now.minute)
        
        # --- 交易时间判断逻辑 ---
        # 1. 早上时段：9:25 开始（含开盘集合竞价）到 11:35（含收盘清理）
        is_morning = (9, 25) <= now_time <= (11, 35)
        
        # 2. 下午时段：12:55 开始（提前准备）到 15:05（含收盘竞价）
        is_afternoon = (12, 55) <= now_time <= (15, 5) # 注意这里是 5，不是 05
        
        # 3. 周末判断：如果是周六(5)或周日(6)
        is_weekend = now.weekday() >= 5

        # 如果不在交易时间，或者是在周末
        if is_weekend or not (is_morning or is_afternoon):
            # 打印提示并进入长时间休眠（例如 10 分钟），避免频繁刷屏
            if is_weekend:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 💤 休息中：周末不复盘。")
            else:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 💤 休息中：非交易时段。")
            
            time.sleep(600) # 休眠 10 分钟
            continue

        for item in StockConfig.MONITOR_LIST:
            symbol = item['symbol']
            try:
                result = agent.invoke({"symbol": symbol})
                analysis = result['analysis']
                print(f"\n【{datetime.now().strftime('%H:%M:%S')} {symbol}】\n{analysis}")
                
                # 提取 JSON 信号决定是否触发外部报警
                match = re.search(r'SIGNAL_JSON:\s*(\{.*\})', analysis)
                if match:
                    sig = json.loads(match.group(1))
                    if sig['probability'] >= StockConfig.PUSH_THRESHOLD:
                        print(f"🔥 高置信度预警: {symbol} {sig['action']} ({sig['probability']}%)")
            except Exception as e:
                print(f"❌ {symbol} 监控异常: {e}")
            time.sleep(2) # 接口频率限制

        time.sleep(StockConfig.INTERVAL_SECONDS)

if __name__ == "__main__":
    run_monitor()