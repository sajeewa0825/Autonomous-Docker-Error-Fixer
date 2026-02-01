from fastapi import FastAPI, Depends
from app.core.config import engine
from app.db.model.document_model import Document
from app.db.model.chat_model import ChatHistory
from app.db.model.containers_model import Container
from app.api.routes.documents.router import router as document_router
from app.api.routes.llm.router import router as llm_router
from app.api.routes.container.router import router as container_router
from app.db.create_vector_index import create_vector_index
from app.api.deps import get_db
from sqlalchemy.orm import Session
from app.services.docker.watcher_manager import start_enabled_container_watchers
from app.services.docker.container_logs import watch_docker_logs
import threading


app = FastAPI()

@app.on_event("startup")
def startup_event():
    Document.metadata.create_all(bind=engine)
    ChatHistory.metadata.create_all(bind=engine)
    Container.metadata.create_all(bind=engine)
    create_vector_index()

    # Start log watcher thread
    # threading.Thread(target=watch_docker_logs, daemon=True).start()
    db: Session = next(get_db())
    try:
        print("🚀 Server started. Loading enabled containers...")
        start_enabled_container_watchers(db)
    finally:
        db.close()

# Main route
app.include_router(document_router, prefix="/document", tags=["document"])
app.include_router(llm_router, prefix="/llm", tags=["llm"])
app.include_router(container_router, prefix="/container", tags=["container"])

@app.get("/")
async def read_root():
    return {"Hello": "World"}