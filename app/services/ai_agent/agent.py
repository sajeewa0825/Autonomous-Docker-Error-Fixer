from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from app.services.ai_agent.state import AgentState
from app.services.ai_agent.tools import retrieve_context_tool
from app.core.loadenv import Settings

# Bind tools so the agent can call them dynamically
tools = [retrieve_context_tool]

llm = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY
)
llm_with_tools = llm.bind_tools(tools)

def llm_call(state: AgentState) -> AgentState:
    """The reasoning node — the agent decides which tools to use."""
    messages = [
        SystemMessage(
            content="You are an intelligent agent capable of deciding when to call the retrieval tool. "
                    "Use it whenever you need more information to answer the user's query. "
                    "You can call it multiple times for different types of data."
        )
    ] + state["messages"]

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def decision_node(state: AgentState):
    """Decide whether to continue reasoning or finish."""
    last_message = state["messages"][-1]
    if not getattr(last_message, "tool_calls", None):
        return "end"
    return "continue"
