from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import os
import logging

logger = logging.getLogger(__name__)

# Ensure static directory exists at import time (for StaticFiles mount)
os.makedirs("static/uploads", exist_ok=True)

from app.core.database import init_db
from app.core.middleware import LocaleMiddleware
from app.identity.router import router as identity_router
from app.wallet.router import router as wallet_router
from app.marketplace.router import router as marketplace_router
from app.kisan.router import router as kisan_router
from app.seva.router import router as seva_router
from app.kutumb.router import router as kutumb_router
from app.enterprise.router import router as enterprise_router
from app.promotions.router import router as promotions_router
from app.cart.router import router as cart_router
from app.ai.router import router as ai_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup lifecycle events: initializes schemas, models and creates tables."""
    # Initialize DB
    await init_db()
    yield

app = FastAPI(
    title="Samuday Platform API",
    description="Community Commerce Super-Platform — Full E-Commerce Edition",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "https://samuday.rngpitai.com",
        "https://samuday-frontend.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply locale context routing middleware globally
app.add_middleware(LocaleMiddleware)

# Mount resource routers
app.include_router(identity_router, prefix="/api/v1")
app.include_router(wallet_router, prefix="/api/v1")
app.include_router(marketplace_router, prefix="/api/v1")
app.include_router(kisan_router, prefix="/api/v1")
app.include_router(seva_router, prefix="/api/v1")
app.include_router(kutumb_router, prefix="/api/v1")
app.include_router(enterprise_router, prefix="/api/v1")
app.include_router(promotions_router, prefix="/api/v1")
app.include_router(cart_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log detailed validation errors for debugging 422 responses."""
    errors = exc.errors()
    logger.error(f"Validation error on {request.method} {request.url.path}: {errors}")
    return JSONResponse(
        status_code=422,
        content={"detail": errors}
    )

@app.get("/")
def read_root():
    """Service status health-check endpoint."""
    return {
        "status": "healthy",
        "service": "Samuday Marketplace API",
        "version": "2.0.0"
    }
