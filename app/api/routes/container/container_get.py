from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.model.containers_model import Container
from app.db.schema.container_schema import ContainerResponse

router = APIRouter()

@router.get("/list", response_model=List[ContainerResponse])
def list_containers(
    enabled: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Container)

    if enabled is not None:
        query = query.filter(Container.enabled == enabled)

    return query.all()
