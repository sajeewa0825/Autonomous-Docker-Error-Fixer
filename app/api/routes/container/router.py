from fastapi import APIRouter
from app.api.routes.container import container_add
from app.api.routes.container import container_get
from app.api.routes.container import container_update

router = APIRouter()
router.include_router(container_add.router)
router.include_router(container_get.router)
router.include_router(container_update.router)
