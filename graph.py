from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import data_collection_node, analysis_node

def create_graph():
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("fetch_data", data_collection_node)
    workflow.add_node("analyze", analysis_node)

    # 设置流程：开始 -> 采集 -> 分析 -> 结束
    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "analyze")
    workflow.add_edge("analyze", END)

    return workflow.compile()