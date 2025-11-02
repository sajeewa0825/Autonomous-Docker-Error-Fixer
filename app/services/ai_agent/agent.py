from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from app.services.ai_agent.state import AgentState
from app.services.ai_agent.tools.Rag_retriever import retrieve_context_tool
from app.services.ai_agent.tools.web_search import web_search
from app.core.loadenv import Settings
from langchain_core.prompts import ChatPromptTemplate
import json
import re

tools = [retrieve_context_tool, web_search]

llm = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY,
)

# Bind tools so the agent can call them dynamically
llm_with_tools = llm.bind_tools(tools)


# The reasoning node
def llm_call(state):
    llm = state["llm"]
    log_line = state["log_line"]
    container_name = state.get("container_name")

    print("continer_name: ", Settings.DOCKER_CONTAINER_NAME)

    try:
        analysis_data = json.loads(state.get("analysis", "{}"))
        log_summary = analysis_data.get("summary", "")
    except Exception:
        log_summary = state.get("analysis", "")

    prompt = ChatPromptTemplate.from_template(
        """
        You are a Docker auto-repair AI agent.
        Analyze the following Docker error and propose an executable fix.

        Log line: {log_line}

        Error Summary: {log_summary}

        Container id: {container_name}

        Respond ONLY in valid JSON format (no markdown, no extra text):
        {{
          "command": "client.containers.get('{container_name}').restart()"
        }}

        If no fix is required, respond with:
        {{
          "command": "NONE"
        }}
        """
    )

    response = llm.invoke(prompt.format(
        log_line=log_line,
        log_summary=log_summary,
        container_name=container_name
    ))
    
    raw_output = response.content.strip()
    cleaned_output = re.sub(r"^```(?:json)?|```$", "", raw_output.strip(), flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(cleaned_output)
        command = parsed.get("command", "NONE")
        print(f"🤖 Suggested fix command: {command}")
        return {"response": command}
    except Exception as e:
        print(f"⚠️ JSON parse failed: {e}\n🧩 Raw LLM Output was: {raw_output}")
        return {"response": "NONE"}
    
# The decision node
# Determines whether to continue reasoning or finish
def decision_node(state: AgentState):
    """Decide whether to continue reasoning or finish."""
    messages = state.get("messages", [])
    if not messages:
        # no messages -> stop
        return "end"

    last_message = messages[-1]
    if not getattr(last_message, "tool_calls", None):
        return "end"
    return "continue"



# What bind_tools does:
# Attaches these tools to the LLM so it knows which tools it can call.
# Enables agentic reasoning: the LLM can dynamically decide to call a tool, receive the output, and continue reasoning.
