from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.v1.router import router
from backend.core.config import settings
from backend.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


# StaticFiles checks that the directory exists when it is mounted.
settings.upload_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="SAB Clothing Extraction API",
    version="0.1.0",
    description="AI-powered clothing extraction service",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)

app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir),
    name="uploads",
)
