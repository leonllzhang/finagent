from typing import TypedDict, Dict, Any

class AgentState(TypedDict):
    symbol: str
    data_metrics: Dict[str, Any]
    analysis: str