from fastapi import APIRouter
from app.api.routes.container import container_add
from app.api.routes.container import container_get
from app.api.routes.container import container_update
from app.api.routes.container import container_delete

router = APIRouter()
router.include_router(container_add.router)
router.include_router(container_get.router)
router.include_router(container_update.router)
router.include_router(container_delete.router)
