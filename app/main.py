from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.modules.booking.router import router as booking_router
from app.modules.catalog.router import router as catalog_router
from app.modules.manifests import event_log
from app.modules.manifests.router import router as manifests_router
from app.modules.matching.router import router as matching_router
from app.modules.tracking.router import router as tracking_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="ORBITA-LINK",
        description="Space cargo brokerage: book fractional launch capacity and track payloads end to end.",
        version="0.1.0",
    )

    # MVP's single event subscriber: append-only event log.
    event_log.register()

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth_router)
    api_v1.include_router(catalog_router)
    api_v1.include_router(manifests_router)
    api_v1.include_router(matching_router)
    api_v1.include_router(booking_router)
    api_v1.include_router(tracking_router)
    app.include_router(api_v1)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Customer web portal (static SPA). Mounted last so /api/v1, /docs and
    # /health keep precedence.
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app


app = create_app()
