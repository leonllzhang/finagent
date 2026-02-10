import time
import os
from datetime import datetime
from graph import create_graph
from config import Config

# 彻底清理环境变量中的代理设置
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

# 强制直连
os.environ['NO_PROXY'] = '*'

def run_monitor():
    # 强制禁用代理
    os.environ['no_proxy'] = '*'
    
    agent = create_graph()
    print(f"🚀 ETF 5分钟短线监控系统已启动...")
    print(f"📡 监控列表: {Config.MONITOR_SYMBOLS} | 频率: {Config.INTERVAL_SECONDS}s")
    print("="*60)

    while True:
        # 只在交易时间运行 (可选)
        now = datetime.now()
        # if not (9 <= now.hour <= 15): 
        #    time.sleep(60); continue

        for symbol in Config.MONITOR_SYMBOLS:
            try:
                # 执行 Agent
                result = agent.invoke({"symbol": symbol})
                
                # 输出分析报告
                print(f"\n【{datetime.now().strftime('%H:%M:%S')} 信号推送: {symbol}】")
                print(result['analysis'])
                print("-" * 40)

                
            except Exception as e:
                print(f"❌ 监控 {symbol} 时发生异常: {e}")
        
        print(f"\n休眠中... 下轮分析将在 {Config.INTERVAL_SECONDS//60} 分钟后开始")
        time.sleep(Config.INTERVAL_SECONDS)

if __name__ == "__main__":
    run_monitor()