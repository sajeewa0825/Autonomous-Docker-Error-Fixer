from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from app.services.ai_agent.state import AgentState
from app.services.ai_agent.tools import retrieve_context_tool
from app.core.loadenv import Settings

tools = [retrieve_context_tool]

llm = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY
)

# Bind tools so the agent can call them dynamically
llm_with_tools = llm.bind_tools(tools)

# The reasoning node
def llm_call(state: AgentState) -> AgentState:
    """The reasoning node — the agent decides which tools to use."""
    messages = [
        SystemMessage(
            content="You are an intelligent agent "
                    "if you don't know the answer call the tool 'retrieve_context' to get relevant information. "
                    "You can call it multiple times for different types of data."
        )
    ] + state["messages"]

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# The decision node
# Determines whether to continue reasoning or finish
def decision_node(state: AgentState):
    """Decide whether to continue reasoning or finish."""
    last_message = state["messages"][-1]
    if not getattr(last_message, "tool_calls", None):
        return "end"
    return "continue"


# What bind_tools does:
# Attaches these tools to the LLM so it knows which tools it can call.
# Enables agentic reasoning: the LLM can dynamically decide to call a tool, receive the output, and continue reasoning.
