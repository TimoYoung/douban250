from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.api import movies, versions, crawl, users
from app.services.scheduler import scheduler

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.posters_dir.mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    init_db()
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(title="Douban Top 250 Tracker", version="0.1.0", lifespan=lifespan)

# API routes
app.include_router(movies.router, prefix="/api/movies", tags=["movies"])
app.include_router(versions.router, prefix="/api/versions", tags=["versions"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(users.router, prefix="/api", tags=["users"])

# Static files for posters
app.mount("/posters", StaticFiles(directory=str(settings.posters_dir)), name="posters")

# Static files for frontend (if built dist exists)
frontend_dist = Path("static")
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
