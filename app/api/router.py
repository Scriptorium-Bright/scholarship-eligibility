from fastapi import APIRouter

from app.api.routers.scholarships import router as scholarships_router

api_router = APIRouter()
api_router.include_router(scholarships_router)
