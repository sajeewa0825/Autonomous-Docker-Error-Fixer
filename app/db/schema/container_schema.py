from pydantic import BaseModel
from typing import Optional

class ContainerCreate(BaseModel):
    name: str
    enabled: int = 1

class ContainerUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[int] = None

class ContainerResponse(BaseModel):
    id: int
    name: str
    enabled: int

    class Config:
        from_attributes = True
