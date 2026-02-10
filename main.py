import time
import os
from datetime import datetime
from graph import create_graph
from config import Config
import re
import json
from notifier import Notifier

# 彻底清理环境变量中的代理设置
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

# 强制直连
os.environ['NO_PROXY'] = '*'

def extract_signal(analysis_text):
    """从 AI 的文本中提取 JSON 信号"""
    try:
        # 使用正则匹配 SIGNAL_JSON: 后面的内容
        match = re.search(r'SIGNAL_JSON:\s*(\{.*\})', analysis_text)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"解析信号失败: {e}")
    return None


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
                
                analysis_text = result['analysis']
                
                # 1. 打印到控制台方便查看
                print(f"\n【{symbol} 分析报告】\n{analysis_text}")

                # 2. 提取信号并判断是否推送
                signal = extract_signal(analysis_text)
                if signal:
                    prob = signal.get('probability', 0)
                    action = signal.get('action', "观望")
                    
                    # 3. 只有当概率超过阈值且不是“观望”时才推送
                    if prob >= Config.PUSH_THRESHOLD and action != "观望":
                        msg = f"标的: {symbol}\n动作: {action}\n置信度: {prob}%\n时间: {datetime.now().strftime('%H:%M')}\n策略: 请及时查看电脑端详细分析。"
                        
                        # 执行推送
                        # Notifier.send_feishu(Config.FEISHU_WEBHOOK, msg)
                        Notifier.send_bark(Config.BARK_KEY, f"ETF预警:{symbol}", f"action:{action}. analyst:{analysis_text}")
                        print(f"🚀 已触发推送信号: {symbol} {action} {prob}%")


                
            except Exception as e:
                print(f"❌ 监控 {symbol} 时发生异常: {e}")
        
        print(f"\n休眠中... 下轮分析将在 {Config.INTERVAL_SECONDS//60} 分钟后开始")
        time.sleep(Config.INTERVAL_SECONDS)

if __name__ == "__main__":
    run_monitor()