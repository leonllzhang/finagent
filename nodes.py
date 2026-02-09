from langchain_openai import ChatOpenAI
from config import Config
from tools import fetch_etf_metrics
from state import AgentState

# 初始化 Qwen 模型
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.API_KEY,
    base_url=Config.BASE_URL,
    temperature=0.1 # 金融分析建议降低随机性
)

def data_collection_node(state: AgentState):
    # 改掉这行提示
    print(f"--- 正在通过 efinance 采集 {state['symbol']} 的实时指标 ---")
    metrics = fetch_etf_metrics(state['symbol'])
    return {"data_metrics": metrics}


def analysis_node(state: AgentState):
    m = state['data_metrics']
    
    # 构建复杂的量化专家提示词
    prompt = f"""
    # Role: 资深资管量化专家 & 首席策略师
    你正在为一个高净值客户分析 ETF 走势。你需要结合趋势、动能、量能以及时间窗口给出极具实战价值的分析。

    # Context: {m['name']} ({state['symbol']}) 深度快照
    - 当前时刻: {m['server_time']} ({"收盘竞价阶段" if m['is_market_closing'] else "盘中交易时段"})
    - 价格动态: 现价 {m['current_price']}, 涨跌幅 {m['pct_change']}%
    - 均线系统: MA20(月线): {m['ma20']:.3f}, MA60(季线): {m['ma60']:.3f}
    - 动能指标: RSI(14): {m['rsi']:.2f}, MACD(12,26,9): Hist {m['macd_hist']:.4f}
    - 成交量能: 量比(Volume Ratio): {m['volume_ratio']:.2f} (注: >1.5代表放量, <0.8代表缩量)

    # Quantitative Reasoning Logic (分维度思考)
    1. **趋势过滤器 (Trend Filter)**: 
       - 现价在 MA20/MA60 之上吗？MA20 是否上穿 MA60（金叉）？判断多头还是空头市场。
    2. **动能共振 (Momentum)**: 
       - RSI 是否在 50 中轴上方？MACD 柱状图是在放大还是收缩（动能背离）？
    3. **量价确认 (Volume Confirmation)**: 
       - 价格的变动是否有成交量的支撑？放量下跌通常是抛售，缩量上涨通常是诱多。
    4. **时间窗口 (Time Edge)**: 
       - 若接近 15:00 收盘，信号的可靠性更高；若在早盘，需警惕虚假突破。

    # Output Format (结构化报告)
    ## 1. 综合走势评分 (0-10分)
    [给出分数，5分为中性，8分以上强看多，3分以下强看空]

    ## 2. 技术面详解 (Bullet Points)
    - **趋势**: [描述现价与 MA20/MA60 的位置关系]
    - **动能**: [分析 RSI 和 MACD 柱状图的斜率]
    - **量能**: [分析量比，判断当前是真突破还是诱多/诱空]

    ## 3. 概率决策
    - **买入 (Buy)**: % [逻辑陈述]
    - **观望 (Wait)**: % [逻辑陈述]
    - **卖出 (Sell)**: % [逻辑陈述]

    ## 4. 操盘手内参 (Actionable Advice)
    - **入场/加仓点**: 具体的支撑位建议。
    - **风险防守位**: 若跌破哪个价位必须止损认输。
    - **短线目标位**: 上行阻力观察。

    请用专业且富有逻辑的语言输出，确保概率总和为100%。
    """
    
    response = llm.invoke(prompt)
    return {"analysis": response.content}