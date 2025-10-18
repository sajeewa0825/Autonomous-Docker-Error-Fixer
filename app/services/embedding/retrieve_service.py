from sqlalchemy import select
from app.db.model.document_model import Document
from app.core.config import SessionLocal
from app.services.embedding.embedding_model import get_embedding_model
from app.core.loadenv import Settings


def retrieve_context( query: str):
    db = SessionLocal()
    embedding_model = get_embedding_model()
    query_vector = embedding_model.encode([query])[0].tolist()

    results = db.scalars(
        select(Document)
        .order_by(Document.embedding.cosine_distance(query_vector))
        .limit(Settings.Top_K_Context)
    ).all()

    db.close()
    return "\n".join([doc.content for doc in results])
