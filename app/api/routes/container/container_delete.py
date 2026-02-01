from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.db.model.containers_model import Container

router = APIRouter()

from fastapi import HTTPException

@router.delete("/delete/{name}")
def delete_container(
    name: str,
    db: Session = Depends(get_db)
):
    db_container = db.query(Container).filter(
        Container.name == name
    ).first()

    if not db_container:
        raise HTTPException(
            status_code=404,
            detail="Container not found"
        )

    db.delete(db_container)
    db.commit()

    return {"message": f"Container '{name}' deleted successfully"}


