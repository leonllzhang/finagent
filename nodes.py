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
    """使用 Qwen3/Qwen2.5 进行金融分析"""
    m = state['data_metrics']
    
    # 针对 Qwen 优化的 Prompt
    prompt = f"""
    你是一个专业的量化投资分析专家。请根据提供的实时指标对 ETF 进行深度分析。
    
    【基本信息】
    ETF名称: {m['name']} ({state['symbol']})
    当前价格: {m['current_price']}
    
    【实时行情】
    - 最新价: {m['current_price']}
    - 今日涨跌幅: {m['pct_change']}%

    【技术指标】
    1. RSI(14): {m['rsi']:.2f} (通常30以下超跌，70以上超买)
    2. MACD指标: 
       - DIFF线: {m['macd_line']:.4f}
       - DEA信号线: {m['macd_signal']:.4f}
       - MACD柱状图: {m['macd_hist']:.4f} (柱状图正负代表多空转换)
    
    【任务要求】
    1. 评估当前趋势（是处于强趋势、震荡还是回调边缘）。
    2. 结合 RSI 和 MACD 的死叉/金叉或背离情况，给出逻辑推导。
    3. 输出三个操作概率：买入、观望、卖出（总和100%）。
    4. 给出具体的心理支撑位和阻力位建议。

    请用专业、简洁的中文回答。
    """
    
    response = llm.invoke(prompt)
    return {"analysis": response.content}