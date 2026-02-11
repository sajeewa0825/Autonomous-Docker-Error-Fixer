from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.config import engine
from app.core.loadenv import Settings

from app.db.model.document_model import Document
from app.db.model.chat_model import ChatHistory
from app.db.model.containers_model import Container

from app.db.create_vector_index import create_vector_index
from app.services.docker.watcher_manager import start_enabled_container_watchers

from app.api.routes.documents.router import router as document_router
from app.api.routes.llm.router import router as llm_router
from app.api.routes.container.router import router as container_router
from app.api.websocket.container_logs_ws import router as ws_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    Document.metadata.create_all(bind=engine)
    ChatHistory.metadata.create_all(bind=engine)
    Container.metadata.create_all(bind=engine)
    create_vector_index()

    db: Session = next(get_db())
    try:
        print("🚀 Server started. Loading enabled containers...")
        start_enabled_container_watchers(db)
    finally:
        db.close()

# Routers
app.include_router(document_router, prefix="/document", tags=["document"])
app.include_router(llm_router, prefix="/llm", tags=["llm"])
app.include_router(container_router, prefix="/container", tags=["container"])
app.include_router(ws_router)

# Static
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/config")
def get_config():
    # If API_BASE_URL not set, UI should use same origin
    return JSONResponse({
        "apiBaseUrl": Settings.API_BASE_URL
    })

@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_path = STATIC_DIR / "index.html"
    html = html_path.read_text(encoding="utf-8")

    # Inject config into HTML (available before UI script runs)
    injected = f"""
    <script>
      window.__APP_CONFIG__ = {{
        apiBaseUrl: {("null" if not Settings.API_BASE_URL else repr(Settings.API_BASE_URL))}
      }};
    </script>
    """

    # Put injected config right before </head>
    if "</head>" in html:
        html = html.replace("</head>", injected + "\n</head>")
    else:
        html = injected + "\n" + html

    return HTMLResponse(html)
