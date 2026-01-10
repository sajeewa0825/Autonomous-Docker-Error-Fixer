from typing import Annotated, Sequence, TypedDict, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared memory for agent conversation and runtime context."""
    
    # all input/output messages
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Runtime context
    llm: Any                      # <-- add this so the graph can hold your LLM instance
    log_line: Optional[str]       # <-- current log line being analyzed
    analysis: Optional[str]       # <-- JSON result from log analysis
    response: Optional[str]       # <-- generated fix or summary
