from pydantic import BaseModel
from typing import Optional


class document(BaseModel):
    document_meta: Optional[str] = None
    content: Optional[str] = None
    message: str

class documentCreate(document):
    pass

class documentResponse(document):
    pass

    class Config:
        from_attributes = True

