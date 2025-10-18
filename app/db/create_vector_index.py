from sqlalchemy import Index
from app.db.model.document_model import Document
from app.core.config import SessionLocal

def create_vector_index():
    db = SessionLocal()
    index = Index(
        'vector_index',
        Document.embedding,
        postgresql_using='hnsw',
        postgresql_with={'m': 16, 'ef_construction': 64},
        postgresql_ops={'embedding': 'vector_cosine_ops'}
    )
    index.create(bind=db.get_bind(), checkfirst=True)  
    db.close()

if __name__ == "__main__":
    create_vector_index()
    print("✅ Vector index created successfully (checked first).")
