"""
Main FastAPI Application for Linux VPN Gateway.
Serves static frontend assets and mounts the REST / SSE API.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .services import subscription as subscription_service

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"


async def background_subscription_updater():
    """Background task to periodically refresh VLESS subscription every 24 hours."""
    while True:
        try:
            await asyncio.sleep(3600)  # Check hourly
            sub_data = subscription_service.load_subscription_data()
            if sub_data.get("url") and sub_data.get("auto_update", True):
                last_updated = sub_data.get("updated_at") or 0
                if time.time() - last_updated >= 24 * 3600:
                    await asyncio.to_thread(subscription_service.refresh_subscription)
        except asyncio.CancelledError:
            break
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    updater_task = asyncio.create_task(background_subscription_updater())
    yield
    updater_task.cancel()
    try:
        await updater_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Linux VPN Gateway",
    description="Minimalist Web Controller for Linux VLESS/Xray VPN Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

# Optional CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API
app.include_router(api_router)

# Mount static web directory
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve single-page frontend application."""
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        return FileResponse(str(BASE_DIR / "web" / "index.html"))
    return FileResponse(str(index_file))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Prevent 404 for browser favicon requests."""
    return FileResponse(str(WEB_DIR / "index.html"), status_code=204)
