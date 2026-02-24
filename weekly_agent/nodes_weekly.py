from langchain_openai import ChatOpenAI
from config_weekly import WeeklyConfig

llm = ChatOpenAI(model=WeeklyConfig.MODEL_NAME, api_key=WeeklyConfig.API_KEY, base_url=WeeklyConfig.BASE_URL)

def weekly_analyze_node(state):
    stock = state['current_stock']
    
    # 这里建议接入真实新闻 API。如果暂时没有，可以让 AI 根据技术异动推测
    prompt = f"""
    # Role: 资深策略分析师 (周度选股)
    
    # 任务: 评估股票 {stock['code']} 在下周上涨的确定性。
    
    # 本周表现:
    - 累计涨幅: {stock['weekly_return']:.2f}%
    - 成交量放大倍数: {stock['vol_increase']:.2f}
    - 趋势位置: 处于MA20均线上方，属于{"放量起步" if stock['vol_increase'] > 1.5 else "平稳运行"}。
    
    # 请结合以下【行业研报/新闻】模拟逻辑分析：
    (此处未来可接入真实新闻文本)

    # 深度分析要求：
    1. 判断这波上涨是【游资短炒】还是【机构趋势建仓】？
    2. 考虑到 T+1 制度，下周一如果冲高回落，风险大吗？
    3. 给出下周预测的上涨概率评分 (0-100)。

    必须在回复最后包含 JSON：
    WEEKLY_RANKING: {{"code": "{stock['code']}", "score": 分数, "reason": "一句话理由"}}
    """
    res = llm.invoke(prompt)
    return {"ai_analysis": res.content}