from langchain_openai import ChatOpenAI
from config import Config
from tools import fetch_etf_metrics_5min
from state import AgentState

llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.API_KEY,
    base_url=Config.BASE_URL,
    temperature=0.1
)

def data_collection_node(state: AgentState):
    print(f"🔍 正在扫描 {state['symbol']} 的 5 分钟级异动...")
    metrics = fetch_etf_metrics_5min(state['symbol'])
    return {"data_metrics": metrics}

def analysis_node(state: AgentState):
    m = state['data_metrics']
    
    # 计算动能斜率
    rsi_slope = "上升 ↑" if m['rsi'] > m['rsi_prev'] else "下降 ↓"
    macd_slope = "扩张 ↑" if abs(m['macd_hist']) > abs(m['macd_hist_prev']) else "收缩 ↓"

    prompt = f"""
    # Role: 日内交易(Scalping)专家
    你负责监控 {m['name']} ({state['symbol']}) 的 5 分钟级波动。

    # 5-Min Snapshot
    - 统计时间: {m['time']}
    - 当前价格: {m['price']} (较5分钟前变化: {m['price_chg_5m']:.2f}%)
    - RSI(14): {m['rsi']:.2f} | 趋势: {rsi_slope}
    - MACD柱线: {m['macd_hist']:.4f} | 趋势: {macd_slope}
    - 成交量爆发比: {m['vol_ratio']:.2f} (注: >2.0 代表极度异常放量)

    # 任务要求
    1. 判断异动性质：是[突破、假拉升、缩量震荡、恐慌砸盘]中的哪一种？
    2. 关注量价共振：价格上涨是否配合了成交量爆发比 > 1.2？
    3. 给出 5 分钟内的操作建议：
       - **Action**: [抢筹 / 减仓 / 待机]
       - **置信度**: X%
    4. 警示：如果 RSI > 80 或 < 20，提醒日内超买/超卖风险。

    请简短、专业地回答。
    """
    response = llm.invoke(prompt)
    return {"analysis": response.content}