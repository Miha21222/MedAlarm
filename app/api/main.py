from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import router
from app.config import load_settings
from app.database.session import init_db
from app.database.session import SessionLocal, session_scope
from app.services.medicine_catalog_service import MedicineCatalogService
from app.version import APP_VERSION


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    if settings.catalog_auto_update:
        try:
            async with session_scope() as session:
                await MedicineCatalogService.refresh(session)
        except Exception:
            logger.exception("Could not refresh the optional MOH medicine catalogue")
    yield


settings = load_settings()
app = FastAPI(title="MedAlarm API", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/version")
async def version(response: Response) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    return {"version": APP_VERSION}


@app.get("/ready")
async def ready() -> dict[str, str]:
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}
