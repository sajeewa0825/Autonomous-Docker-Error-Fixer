from app.services.ai_agent.graph import build_agentic_rag_graph

def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        message.pretty_print()

if __name__ == "__main__":
    app = build_agentic_rag_graph()
    inputs = {"messages": [("user", "Explain who is sajeewa kumarasingha "
                                    "Retrieve information and any relevant context data if needed.")]}

    print_stream(app.stream(inputs, stream_mode="values"))
