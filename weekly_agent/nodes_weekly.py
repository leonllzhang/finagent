import json
import re
from langchain_openai import ChatOpenAI
from config_weekly import WeeklyConfig

llm = ChatOpenAI(
    model=WeeklyConfig.MODEL_NAME, 
    api_key=WeeklyConfig.API_KEY, 
    base_url=WeeklyConfig.BASE_URL,
    temperature=0.1
)

def market_sentiment_node(state):
    """分析新闻，输出全球避险系数"""
    news_context = state.get('macro_news', "暂无新闻")
    prompt = f"""
    # Role: 全球宏观策略研究员
    请评估当前市场的“避险情绪”。
    【实时新闻电报】:
    {news_context}
    
    # 输出要求:
    给出一个【全球避险系数】(0-100分)：
    - 70-100: 极度恐慌（战争、金融危机），建议避险。
    必须包含 JSON:
    MARKET_SENTIMENT: {{"risk_score": 分数, "theme": "核心风险", "safe_sectors": ["军工", "石油", "黄金", "电力"]}}
    """
    res = llm.invoke(prompt)
    try:
        match = re.search(r'MARKET_SENTIMENT:\s*(\{.*\})', res.content)
        sentiment_data = json.loads(match.group(1))
    except:
        sentiment_data = {"risk_score": 50, "theme": "未知", "safe_sectors": []}
    return {"sentiment_analysis": sentiment_data}

def weekly_analyze_node(state):
    """结合技术面和风控评分进行选股"""
    stock = state['current_stock']
    sentiment = state['sentiment_analysis']
    
    prompt = f"""
    # Role: 资管风控总监
    【宏观风险分】: {sentiment['risk_score']} | 【核心风险】: {sentiment['theme']}
    【避险资产方向】: {', '.join(sentiment['safe_sectors'])}
    
    【个股数据 ({stock['code']})】:
    - 上周涨幅: {stock['weekly_return']:.2f}% | 量能比: {stock['vol_increase']:.2f}
    
    # 强制逻辑:
    1. 如果【风险分】> 75，且该股不属于上述避险方向，上涨评分严禁超过 60分。
    2. 判定该股是否具备抗地缘打击的属性。

    必须包含 JSON：
    WEEKLY_RANKING: {{"code": "{stock['code']}", "score": 分数, "reason": "结合风险的研判理由"}}
    """
    res = llm.invoke(prompt)
    return {"ai_analysis": res.content}