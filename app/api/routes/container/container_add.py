from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.db.model.containers_model import Container
from app.db.schema.container_schema import ContainerCreate, ContainerResponse

router = APIRouter()

@router.post("/add", response_model=ContainerResponse)
def add_container(
    container: ContainerCreate,
    db: Session = Depends(get_db)
):
    # Check if container already exists
    existing = db.query(Container).filter(
        Container.name == container.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Container already exists"
        )

    new_container = Container(
        name=container.name,
        enabled=container.enabled
    )

    db.add(new_container)
    db.commit()
    db.refresh(new_container)

    return new_container
