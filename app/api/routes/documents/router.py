from fastapi import APIRouter
from app.api.routes.documents import documents_add

router = APIRouter()
router.include_router(documents_add.router)



