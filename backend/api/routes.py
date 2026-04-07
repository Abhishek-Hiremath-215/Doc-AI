from fastapi import APIRouter
from . import admin, projects, query, upload, users

router = APIRouter()

router.include_router(users.router, tags=["users"])
router.include_router(admin.router, tags=["admin"])
router.include_router(projects.router, tags=["projects"])
router.include_router(upload.router, tags=["upload"])
router.include_router(query.router, tags=["query"])
