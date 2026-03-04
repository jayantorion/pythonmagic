from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize logging and database tables
    setup_logging()
    logger.info("Initializing AI Job Search & Application Intelligence Platform...")
    await init_db()
    logger.info(f"Database initialized. Engine: {'SQLite' if settings.is_sqlite else 'PostgreSQL'}")
    yield
    # Shutdown: Clean up resources if necessary
    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.APP_TITLE,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.APP_TITLE,
        "docs": "/docs",
        "version": "1.0.0",
        "database": "sqlite" if settings.is_sqlite else "postgresql",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
