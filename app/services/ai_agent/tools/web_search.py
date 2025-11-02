from langchain_core import tools
from langchain_community.tools import DuckDuckGoSearchRun

@tools.tool("web_search")
def web_search(query: str) -> str:
    """Perform a web search for the given query and return the results."""
    search = DuckDuckGoSearchRun()
    try:
        results = search.run(query)
        return results
    except Exception as e:
        return f"Error during web search: {str(e)}"
