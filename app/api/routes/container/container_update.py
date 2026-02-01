from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.db.model.containers_model import Container
from app.db.schema.container_schema import  ContainerResponse , ContainerUpdate
from app.services.docker.watcher_manager import stop_watcher, start_watcher

router = APIRouter()

from fastapi import HTTPException

@router.patch("/update/{container_id}", response_model=ContainerResponse)
def update_container(
    container_name: str,
    container: ContainerUpdate,
    db: Session = Depends(get_db)
):
    db_container = db.query(Container).filter(
        Container.name == container_name
    ).first()

    if not db_container:
        raise HTTPException(
            status_code=404,
            detail="Container not found"
        )

    if container.name is not None:
        db_container.name = container.name

    if container.enabled is not None:
        db_container.enabled = container.enabled

    db.commit()
    db.refresh(db_container)

    # Manage watcher based on enabled status
    if container.enabled == 1:
        start_watcher(db_container.name)
    else:
        stop_watcher(db_container.name)

    return db_container

