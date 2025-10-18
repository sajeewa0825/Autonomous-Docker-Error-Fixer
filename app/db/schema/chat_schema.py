from pydantic import BaseModel
from typing import List
from datetime import datetime

class ChatCreate(BaseModel):
    user_id: int
    prompt: str

class ChatResponse(BaseModel):
    id: int
    user_prompt: str
    ai_response: str
    timestamp: datetime

    class Config:
        from_attributes = True
