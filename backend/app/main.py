import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_tables, SessionLocal
from app.routers import news, favorites, broadcast, sources
from app.workers.fetcher import start_scheduler, stop_scheduler, run_fetch_cycle
from app.services.ingestion import seed_sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting AI News Dashboard...")
    create_tables()

    db = SessionLocal()
    try:
        seed_sources(db)
    finally:
        db.close()

    start_scheduler()

    # Trigger an initial fetch so the dashboard isn't empty
    asyncio.create_task(run_fetch_cycle())

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    stop_scheduler()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(news.router, prefix="/api")
app.include_router(favorites.router, prefix="/api")
app.include_router(broadcast.router, prefix="/api")
app.include_router(sources.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}