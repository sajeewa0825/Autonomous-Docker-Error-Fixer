from app.services.ai_agent.graph import build_agentic_rag_graph
from fastapi import APIRouter, status, HTTPException
from app.db.schema.llm_schema import llmChat
from langchain_core.messages import BaseMessage

router = APIRouter()


def collect_stream(stream):
    """
    Collects messages from the agent stream and returns the last AI response content.
    """
    last_content = ""
    for s in stream:
        message: BaseMessage = s["messages"][-1]
        # If message has pretty_print, call it to display (optional)
        if hasattr(message, "pretty_print"):
            message.pretty_print()
        last_content = getattr(message, "content", str(message))
    return last_content


@router.post("/", status_code=status.HTTP_200_OK)
async def llm_request(request: llmChat):
    """Handle LLM requests and return AI response."""
    prompt = request.prompt

    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    # Build the agentic RAG graph
    app = build_agentic_rag_graph()

    # Prepare inputs for the agent
    inputs = {"messages": [("user", prompt)]}

    # Run the agent and collect the AI response
    ai_response = collect_stream(app.stream(inputs, stream_mode="values"))

    # Return AI response in API
    return {"response": ai_response}
