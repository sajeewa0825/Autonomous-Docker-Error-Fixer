from fastapi import APIRouter
from app.api.routes.llm import llm_request

router = APIRouter()
router.include_router(llm_request.router)



