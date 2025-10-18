from langchain_core.tools import tool
from app.services.embedding.retrieve_service import retrieve_context  # if you have it

@tool("retrieve_context", return_direct=False)
def retrieve_context_tool(query: str) -> str:
    """Retrieve relevant context for the given query from vector DB."""
    try:
        return retrieve_context(query)
    except Exception as e:
        return f"Error during retrieval: {str(e)}"
