"""FastAPI main.py with Windows async fix"""
import sys
import asyncio

# 🔥 WINDOWS FIX: Must be before any other imports
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import datetime
import logging
import os
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt

from auth import ALGORITHM, SECRET_KEY
from dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_org_admin,
    get_current_super_admin,
    get_db
)
from schemas import Token, UserCreate, UserLogin
from database import engine
from models import Base, User
from core import config

# Fixed Routers imports - made consistent
from api.users import login_user, register_user, router as users_router
from api.admin import UserOut, router as admin_router
from api.projects import router as projects_router
from api.upload import router as upload_router
from api.query import router as query_router
from api.organizations import router as org_router
from api.scraper import router as scraper_router # Fixed this import
from api.chat import router as chat_router

# Logger Setup
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
logger.info("[INFO] Starting DocAI FastAPI server...")

# Initialize DB Tables
Base.metadata.create_all(bind=engine)

# FastAPI App Initialization
app = FastAPI(
    title="DocAI Backend",
    description="Backend for DocAI RAG SaaS platform",
    version="1.0.0"
)

# CORS Middleware
origins = [
    config.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files (for charts)
if not os.path.exists("generated_charts"):
    os.makedirs("generated_charts")
app.mount("/generated_charts", StaticFiles(directory="generated_charts"), name="generated_charts")

# Include Routers - removed duplicates
app.include_router(scraper_router, prefix="/scraper", tags=["Scraper"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(upload_router, prefix="/upload", tags=["Upload"])
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(org_router, prefix="/organizations", tags=["Organizations"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])

# Debug routes
print("\n=== DEBUG: All Registered Routes ===")
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        print(f"{list(route.methods)} {route.path}")
print("=== END DEBUG ===\n")

# Health Check Endpoint
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "DocAI Backend is running 🚀"}

# Auth Shortcut Routes
@app.post("/login", response_model=Token, tags=["Auth"])
def login(user_in: UserLogin, db=Depends(get_db)):
    return login_user(user_in=user_in, db=db)

@app.post("/register", response_model=UserOut, tags=["Auth"])
def register(user_in: UserCreate, db=Depends(get_db)):
    return register_user(user_in=user_in, db=db)

# Admin-only Route
@app.get("/admin/dashboard", tags=["Admin"])
def admin_dashboard(current_user: User = Depends(get_current_super_admin)):
    return {"message": f"Welcome Admin: {current_user.email}"}

# Authenticated User Route
@app.get("/protected", tags=["Debug"])
def protected(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hello, {current_user.email}. Your role is {current_user.role}"}

# Token Debugging Utility
@app.post("/debug/token", tags=["Debug"])
async def debug_token(request: Request):
    data = await request.json()
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp:
            payload["expires_at"] = datetime.datetime.utcfromtimestamp(exp).isoformat()
        logger.info(f"[DEBUG] Decoded token payload: {payload}")
        return {"decoded_payload": payload}
    except JWTError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")

# Swagger Redirect
@app.get("/docs-redirect", include_in_schema=False)
async def redirect_docs():
    return RedirectResponse(url="/docs")

# Graceful Shutdown
@app.on_event("shutdown")
def shutdown_event():
    try:
        config.graph_manager.close()
        logger.info("[INFO] Neo4j connection closed gracefully.")
    except Exception as e:
        logger.warning(f"[WARN] Shutdown cleanup failed: {e}")

logger.info("[INFO] DocAI FastAPI server started and ready.")
