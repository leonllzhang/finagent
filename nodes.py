from langchain_openai import ChatOpenAI
from config import Config
from tools import fetch_etf_enhanced_metrics
from state import AgentState

llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.API_KEY,
    base_url=Config.BASE_URL,
    temperature=0.1
)

def data_collection_node(state: AgentState):
    print(f"📊 正在通过新浪财经采集 {state['symbol']} 多周期深度指标...")
    metrics = fetch_etf_enhanced_metrics(state['symbol'])
    return {"data_metrics": metrics}

def analysis_node(state: AgentState):
    m = state['data_metrics']
    
    # 核心盈利逻辑 Prompt
    prompt = f"""
    # Role: 资深量化交易员 (专攻多周期共振策略)
    
    # Market Context
    - 标的: {state['symbol']} | 时间: {m['time']}
    - 大盘(沪深300)5分钟走势: {m['market_index_pct']:.2f}% ({"走强" if m['market_index_pct'] > 0 else "走弱"})
    
    # Strategy Dimension 1: 日线级大趋势 (定性)
    - 趋势过滤器: {m['daily_trend']} (价格运行在MA20均线{"上方" if m['daily_trend']=='多头' else "下方"})
    - 长线超买超卖: 日线RSI={m['daily_rsi']:.2f}
    
    # Strategy Dimension 2: 5分钟级日内异动 (择时)
    - 当前价格: {m['price']} | 5分钟涨跌: {m['chg_5m']:.2f}%
    - 日内量能爆发比: {m['vol_ratio_5m']:.2f} (注: >1.5代表有主力异动)
    - 动能指标: 5min-RSI={m['rsi_5m']:.2f}, MACD柱线={m['macd_hist_5m']:.4f}

    # 盈利决策逻辑 (Reasoning)
    1. **趋势对齐**: 只有在【日线多头】环境下，5分钟的金叉和放量突破才是高胜率买点。
    2. **量价确认**: 价格拉升必须配合量比 > 1.2。
    3. **情绪风险**: 若大盘走弱且标的处于 5min-RSI > 75，需警惕冲高回落。

    # Output Requirements
    请给出以下决策并陈述理由：
    1. **当前阶段研判**: (如：趋势回调、放量突破、缩量阴跌等)
    2. **操作置信度评分**: (0-10分，分数越高盈利概率越大)
    3. **推送结论**: [买入介入 / 继续持有 / 观望等待 / 逢高止盈]
    
    请在回答末尾务必包含此JSON：
    SIGNAL_JSON: {{"symbol": "{state['symbol']}", "action": "推送结论", "probability": 分数*10}}
    """
    
    response = llm.invoke(prompt)
    return {"analysis": response.content}