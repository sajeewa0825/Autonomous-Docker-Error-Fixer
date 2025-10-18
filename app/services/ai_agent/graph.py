# app/services/ai_agent/graph.py
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.services.ai_agent.state import AgentState
from app.services.ai_agent.agent import llm_call, decision_node, tools

def build_agentic_rag_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", llm_call)
    tool_node = ToolNode(tools=tools)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        decision_node,
        {
            "continue": "tools",
            "end": END,
        },
    )
    graph.add_edge("tools", "agent")

    return graph.compile()
