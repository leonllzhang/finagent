import json
import re
from langchain_openai import ChatOpenAI
from config import Config
from tools import fetch_etf_enhanced_metrics
from state import AgentState

# 初始化模型
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.API_KEY,
    base_url=Config.BASE_URL,
    temperature=0.1 
)

def data_collection_node(state: AgentState):
    """数据采集节点"""
    symbol = state['symbol']
    print(f"📊 正在扫描 {symbol} 的五维深度指标 (含VWAP与加速度)...")
    try:
        metrics = fetch_etf_enhanced_metrics(symbol)
        return {"data_metrics": metrics}
    except Exception as e:
        print(f"❌ 数据采集失败: {e}")
        raise e

def analysis_node(state: AgentState):
    """决策分析节点：进化版量化逻辑"""
    m = state['data_metrics']
    symbol = state['symbol']
    
    # 进化版提示词：加入了“主升浪”和“极弱势”判定逻辑
    prompt = f"""
    # Role: 顶级日内波段专家 (专攻单边趋势与极值反转)
    
    # Market Snapshot: {symbol} @ {m['time']}
    - 现价: {m['price']} | 5min涨跌: {m['chg_5m']:.2f}%
    - 日内均价(VWAP): {m['vwap']:.3f} | 偏离度: {m['vwap_dist']:.2f}% ({m['vwap_status']})
    - 波动通道(BBands): {m['bb_status']}
    - 动能斜率(MACD Slope): {m['macd_slope']:.4f} | 状态: {m['macd_slope_desc']}
    - 活跃度: 5min量比 {m['vol_ratio_5m']:.2f} | RSI {m['rsi_5m']:.2f}
    - 环境: 日线{m['daily_trend']} | 沪深300指数 {m['market_index_pct']:.2f}%

    # 深度量化策略决策逻辑 (必须严格遵守):
    
    1. **【识别单边主升浪 - 解决踏空问题】**:
       - 如果 价格处于“向上突破上轨” 且 处于“VWAP上方” 且 MACD斜率“正在增强”：
       - 判定为【主升浪加速】。此时即使 RSI > 75，也严禁建议“观望”。
       - 结论：建议【买入/持有】，置信度应在 80% 以上。

    2. **【识别单边杀跌 - 解决接飞刀问题】**:
       - 如果 价格处于“向下跌破下轨” 且 处于“VWAP下方”：
       - 判定为【机构砸盘/多头踩踏】。此时即使 RSI < 25 且斜率微回升，也严禁抄底。
       - 结论：建议【观望/卖出】，买入置信度必须低于 40%。

    3. **【震荡回归逻辑】**:
       - 如果价格在布林带内运行，且量比 < 1.0，MACD斜率趋于0：
       - 判定为【无序震荡】。建议【观望】，置信度 60% 左右。

    4. **【极端偏离预警】**:
       - 如果价格偏离 VWAP > 2.0% 且量比开始萎缩：
       - 判定为【短线力竭】。建议【逢高止盈】。

    # 输出要求：
    请提供：1. 阶段研判；2. 逻辑推导（重点分析VWAP与斜率）；3. 操盘建议（买入/持有/卖出/观望）。
    
    必须在末尾包含此 JSON 总结：
    SIGNAL_JSON: {{"symbol": "{symbol}", "action": "xxx", "probability": XX, "stop_loss": {m['vwap'] if m['price'] > m['vwap'] else m['bb_lower']}}}
    """
    
    try:
        response = llm.invoke(prompt)
        return {"analysis": response.content}
    except Exception as e:
        print(f"❌ AI 分析报错: {e}")
        return {"analysis": "分析暂时不可用"}