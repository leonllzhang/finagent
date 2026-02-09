from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    symbol: str               # ETF代码
    data_metrics: Dict[str, Any] # 计算出的技术指标数据
    analysis: str             # LLM 生成的分析报告
    history: List[str]        # 简单的对话历史