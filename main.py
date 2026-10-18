"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from database import Base, engine
from models import Event  # noqa: F401 — import registers the model
from routers import webhooks
from worker import worker_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and start the background worker on startup."""
    Base.metadata.create_all(bind=engine)

    worker_task = asyncio.create_task(worker_loop())
    logger = logging.getLogger("main")
    logger.info("Application startup complete")

    yield

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Webhook Relay",
    version=settings.version,
    description="Reliable webhook receiver with retries and idempotency.",
    lifespan=lifespan,
)

app.include_router(webhooks.router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
    }


@app.get("/health")
def health():
    return {"status": "healthy"}