"""
DevMaster FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings
from .database import sync_engine, Base, init_db
from .routers import orchestration
from .core.events import event_bus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devmaster")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    
    Start and stop background tasks.
    """
    # Startup
    logger.info("Starting DevMaster API")
    
    # Start event bus in background
    import asyncio
    event_task = asyncio.create_task(event_bus.start())
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevMaster API")
    await event_bus.stop()
    event_task.cancel()


# Create all tables (for development only)
# In production, use Alembic migrations
# Base.metadata.create_all(bind=sync_engine)  # Commented out - database not running

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(orchestration.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to DevMaster API",
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
    }