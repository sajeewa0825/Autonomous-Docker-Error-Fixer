from fastapi import FastAPI
from app.core.config import engine
from app.db.model.document_model import Document
from app.db.model.chat_model import ChatHistory
from app.api.routes.documents.router import router as document_router
from app.api.routes.llm.router import router as llm_router
from app.db.create_vector_index import create_vector_index


app = FastAPI()

@app.on_event("startup")
def startup_event():
    Document.metadata.create_all(bind=engine)
    ChatHistory.metadata.create_all(bind=engine)
    create_vector_index()

# Main route
app.include_router(document_router, prefix="/document", tags=["document"])
app.include_router(llm_router, prefix="/llm", tags=["llm"])

@app.get("/")
async def read_root():
    return {"Hello": "World"}