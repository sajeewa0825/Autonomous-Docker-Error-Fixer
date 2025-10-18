from app.services.ai_agent.graph import build_agentic_rag_graph

# Build the graph
app = build_agentic_rag_graph()
graph = app.get_graph()

# Get PNG bytes
png_bytes = graph.draw_mermaid_png()

# Save to a file
with open("Architecture.png", "wb") as f:
    f.write(png_bytes)

print("Graph saved as Architecture.png")
