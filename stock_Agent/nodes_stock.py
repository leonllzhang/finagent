import json
import re
from langchain_openai import ChatOpenAI
from config_stock import StockConfig
from tools_stock import fetch_stock_full_metrics
from state_stock import AgentState

llm = ChatOpenAI(
    model=StockConfig.MODEL_NAME, 
    api_key=StockConfig.API_KEY, 
    base_url=StockConfig.BASE_URL, 
    temperature=0.1
)

def data_collection_node(state: AgentState):
    symbol = state['symbol']
    # 从配置中查找对应的行业代码
    sector = next(item['sector'] for item in StockConfig.MONITOR_LIST if item['symbol'] == symbol)
    print(f"📊 正在采集 {symbol} (参考板块 {sector}) 的全量特征...")
    metrics = fetch_stock_full_metrics(symbol, sector)
    return {"data_metrics": metrics}

def analysis_node(state: AgentState):
    m = state.get('data_metrics', {})
    symbol = state.get('symbol', 'Unknown')
    
    # 安全提取数值，防止 KeyError
    price = m.get('price', 0)
    vwap = m.get('vwap', 0)
    vol_ratio = m.get('vol_ratio', 1.0)
    macd_slope = m.get('macd_slope', 0)
    dist_limit = m.get('dist_to_limit', 0)

    prompt = f"""
    # Role: 顶级个股短线专家 (专攻异动博弈)
    分析标的: {m.get('name', symbol)} ({symbol})
    
    # 1. 实时量化快照
    - 价格: {price} | 5min涨跌: {m.get('chg_5m', 0):.2f}%
    - 均价线(VWAP): {vwap:.3f} | 状态: {m.get('vwap_status', '未知')}
    - 换手率: {m.get('turnover', 0)}% | 5min量比: {vol_ratio:.2f}
    - 动能斜率: {macd_slope:.4f} ({m.get('macd_slope_desc', '持平')})
    - 布林带: {m.get('bb_status', '正常')} | RSI(5m): {m.get('rsi_5m', 50):.2f}
    - 行业环境: 相关板块涨跌 {m.get('sector_pct', 0):.2f}% | 距涨停: {dist_limit:.2f}%

    # 2. 核心操盘逻辑
    1. **识别主升浪**: 价格在VWAP上 + 突破布林上轨 + 斜率增强 + 量比>1.5。判定为游资抢筹，建议【买入/持有】。
    2. **识别接飞刀**: 价格在VWAP下 + 跌破布林下轨 + 斜率加速向下。判定为机构砸盘，严禁抄底。
    3. **识别洗盘回踩**: 缩量回踩VWAP或布林中轨，斜率未转负。判定为【低吸】机会。

    # 3. 输出要求
    请详细给出：1. 资金面异动定性；2. 置信度评分(0-100)；3. 操作结论。
    
    必须在末尾包含此 JSON 总结：
    SIGNAL_JSON: {{"symbol": "{symbol}", "action": "买入/卖出/观望/持有", "probability": 评分, "stop_loss": {vwap if price > vwap else price * 0.98}}}
    """
    
    try:
        res = llm.invoke(prompt)
        return {"analysis": res.content}
    except Exception as e:
        print(f"❌ AI 分析异常: {e}")
        return {"analysis": "AI 分析暂时失败"}

# 辅助解析函数 (供 main_stock.py 使用)
def extract_signal(text):
    try:
        match = re.search(r'SIGNAL_JSON:\s*(\{.*\})', text)
        if match:
            return json.loads(match.group(1))
    except:
        return None