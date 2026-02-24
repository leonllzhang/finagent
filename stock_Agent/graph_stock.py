from langgraph.graph import StateGraph, END
from state_stock import AgentState
from nodes_stock import data_collection_node, analysis_node

def create_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("fetch_data", data_collection_node)
    workflow.add_node("analyze", analysis_node)
    
    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "analyze")
    workflow.add_edge("analyze", END)
    
    return workflow.compile()