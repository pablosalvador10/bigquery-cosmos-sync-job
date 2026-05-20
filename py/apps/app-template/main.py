"""FastAPI application entrypoint with lifespan, CORS, and telemetry setup."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.chat import router as chat_router
from core.config import settings
from core.logging import configure_logging
from core.telemetry import configure_tracing, instrument_fastapi


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    configure_tracing(settings)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

instrument_fastapi(app)
app.include_router(chat_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
