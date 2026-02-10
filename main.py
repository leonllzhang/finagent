import time
import os
from datetime import datetime
from graph import create_graph
from config import Config

def run_monitor():
    # 强制禁用代理，确保直连 Tushare 和 Qwen (如果 Qwen 在国内不需要代理)
    os.environ['no_proxy'] = '*'
    
    agent = create_graph()
    print(f"🚀 基于 Tushare 的 ETF 5分钟级雷达启动...")
    print(f"📡 监控列表: {Config.MONITOR_SYMBOLS}")
    print("="*60)

    while True:
        now = datetime.now()
        # 简单的交易时间过滤 (A股交易时间)
        if not (9 <= now.hour <= 15):
            print(f"[{now.strftime('%H:%M:%S')}] 非交易时间，休眠中...")
            time.sleep(600)
            continue

        for symbol in Config.MONITOR_SYMBOLS:
            try:
                # 运行 Agent 分析
                result = agent.invoke({"symbol": symbol})
                
                print(f"\n【{datetime.now().strftime('%H:%M:%S')} 信号推送: {symbol}】")
                print(result['analysis'])
                print("-" * 40)
                
                # Tushare 频率控制：每只分析完稍作停顿
                time.sleep(2) 
                
            except Exception as e:
                print(f"❌ 监控 {symbol} 失败: {e}")
        
        print(f"\n下轮轮询将在 {Config.INTERVAL_SECONDS//60} 分钟后开始...")
        time.sleep(Config.INTERVAL_SECONDS)

if __name__ == "__main__":
    run_monitor()