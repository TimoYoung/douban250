from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.api import movies, versions, crawl, users, pending_matches
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
app.include_router(pending_matches.router, prefix="/api/pending-matches", tags=["pending-matches"])
app.include_router(users.router, prefix="/api", tags=["users"])

# Static files for posters
app.mount("/posters", StaticFiles(directory=str(settings.posters_dir)), name="posters")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Frontend static files (must be last — catch-all)
frontend_dist = Path("static")
if frontend_dist.exists():
    @app.api_route("/{path:path}", methods=["GET"])
    async def serve_frontend(request: Request, path: str):
        # Let API routes pass through
        if path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        file_path = frontend_dist / path
        if path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
