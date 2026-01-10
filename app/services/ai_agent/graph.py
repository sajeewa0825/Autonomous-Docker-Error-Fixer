from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.services.ai_agent.state import AgentState
from app.services.ai_agent.agent import llm_call, decision_node, tools

from app.services.ai_agent.log_analysis import analyze_log_line
from app.services.ai_agent.error_decision import is_error_log

def build_agentic_rag_graph():
    graph = StateGraph(AgentState)

    # New Docker log analyzer node
    graph.add_node("log_analyzer", analyze_log_line)

    # Agent node that uses llm_call to fixes Docker issues
    graph.add_node("agent", llm_call)

    # Tool node for executing actions
    graph.add_node("tools", ToolNode(tools=tools))



    # Flow:
    graph.set_entry_point("log_analyzer")
    graph.add_conditional_edges(
        "log_analyzer",
        is_error_log,
        {
            "error": "agent",
            "ok": END,
        },
    )

    # Keep your existing RAG flow for the "agent"
    graph.add_conditional_edges(
        "agent",
        decision_node,
        {
            "continue": "tools",
            "end": END,
        },
    )

    # Tool node flows back to agent for further reasoning
    graph.add_edge("tools", "agent")

    return graph.compile()
