from langchain_core.tools import tool
from app.services.embedding.retrieve_service import retrieve_context 

@tool("retrieve_context", return_direct=False)
def retrieve_context_tool(query: str) -> str:
    """Retrieve relevant context for the given query from vector DB."""
    try:
        return retrieve_context(query)
    except Exception as e:
        return f"Error during retrieval: {str(e)}"

# why return_direct=False?
# Allows the LLM to reason about the tool output before sending it to the user.
# Supports multi-step agentic reasoning.
# return_direct=True → The tool’s raw output is returned directly to the user or next node.