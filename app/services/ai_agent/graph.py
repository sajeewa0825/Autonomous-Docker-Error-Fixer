from langgraph.graph import StateGraph, END
from app.services.ai_agent.state import AgentState
from app.services.ai_agent.log_analysis import analyze_log_line
from app.services.ai_agent.agent import llm_call
from app.services.ai_agent.error_decision import is_error_log

def build_agentic_rag_graph():
    graph = StateGraph(AgentState)

    graph.add_node("log_analyzer", analyze_log_line)
    graph.add_node("agent", llm_call)

    graph.set_entry_point("log_analyzer")
    graph.add_conditional_edges(
        "log_analyzer",
        is_error_log,
        {"error": "agent", "ok": END},
    )

    graph.add_edge("agent", END)

    return graph.compile()
