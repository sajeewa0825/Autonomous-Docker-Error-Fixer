from pydantic import BaseModel

class llm(BaseModel):
    prompt: str

class llmChat(BaseModel):
    prompt: str


    class Config:
        from_attributes = True
