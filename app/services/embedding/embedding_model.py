from sentence_transformers import SentenceTransformer
from app.core.loadenv import Settings

# Cache globally (loaded once)
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(Settings.EMBEDDING_MODEL) 
    return _model
