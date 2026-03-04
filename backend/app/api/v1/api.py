from fastapi import APIRouter
from app.api.v1.candidate import router as candidate_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.resume import router as resume_router
from app.api.v1.applications import router as applications_router

api_router = APIRouter()
api_router.include_router(candidate_router)
api_router.include_router(jobs_router)
api_router.include_router(resume_router)
api_router.include_router(applications_router)
