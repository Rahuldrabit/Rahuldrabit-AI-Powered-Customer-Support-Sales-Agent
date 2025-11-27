"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.models.database import engine, Base
from app.api.routes import webhooks, messages, analytics, admin
from app.api.routes import oauth
from fastapi import APIRouter
from app.utils.logger import setup_logging

# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Powered Customer Support & Sales Agent",
    lifespan=lifespan
)

# Instrument with Prometheus
if settings.enable_metrics:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with existing prefixes
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(messages.router, prefix="/messages", tags=["Messages"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(oauth.router, prefix="/oauth", tags=["OAuth"])

# Alias router for top-level /agent/* endpoints
agent_router = APIRouter(tags=["Agent"])

@agent_router.post("/configure")
async def agent_configure_alias(
    config_key: str,
    config_value: str,
    description: str | None = None
):
    # Delegate to existing handler mounted under /admin
    from app.api.routes.admin import configure_agent
    return await configure_agent(
        config_key=config_key,
        config_value=config_value,
        description=description,
    )

@agent_router.get("/status")
async def agent_status_alias():
    from app.api.routes.admin import get_agent_status
    return await get_agent_status()

@agent_router.post("/train")
async def agent_train_alias():
    from app.api.routes.admin import train_agent
    return await train_agent()

app.include_router(agent_router, prefix="/agent")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment
    }
