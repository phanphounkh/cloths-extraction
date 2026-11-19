from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.session import get_db
from backend.models.image_job import STATUS_COMPLETED, STATUS_FAILED, ImageJob
from backend.schemas.image_job import ImageJobOut
from backend.services.image_service import MAX_UPLOAD_BYTES, encode_png, normalize_upload
from backend.services.openrouter import generate_garment

router = APIRouter(prefix="/images", tags=["images"])

Garment = Literal["shirt", "jacket", "dress", "pants", "skirt", "shoes", "other"]


def upload_url(path: str | None) -> str | None:
    # Path(...).name also handles rows saved with absolute paths.
    return f"/uploads/{Path(path).name}" if path else None


def serialize(job: ImageJob) -> ImageJobOut:
    return ImageJobOut(
        id=job.id,
        status=job.status,
        garment=job.garment,
        input_url=upload_url(job.input_path) or "",
        output_url=upload_url(job.output_path),
        error=job.error,
        created_at=job.created_at,
    )


async def save_file(name: str, data: bytes) -> None:
    await run_in_threadpool((settings.upload_dir / name).write_bytes, data)


@router.post("/extract", response_model=ImageJobOut)
async def extract(
    file: Annotated[UploadFile, File(description="Photo of a person wearing the garment")],
    db: Annotated[AsyncSession, Depends(get_db)],
    garment: Annotated[Garment, Form()] = "shirt",
    instruction: Annotated[str, Form(max_length=500)] = "",
):
    if not settings.openrouter_configured:
        raise HTTPException(503, "AI generation is not configured: set OPENROUTER_API_KEY.")

    # Read one byte past the limit so oversized files are detected
    # without loading arbitrarily large uploads into memory.
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    # Pillow work is CPU-bound; keep it off the event loop.
    normalized = await run_in_threadpool(normalize_upload, raw)

    job = ImageJob(garment=garment, input_path="")
    db.add(job)
    await db.flush()  # assigns job.id

    input_name = f"{job.id}-input.jpg"
    await save_file(input_name, normalized)
    job.input_path = input_name
    # Commit before the slow AI call so no DB connection is held while waiting.
    await db.commit()

    try:
        generated = await generate_garment(normalized, garment, instruction)
        try:
            png = await run_in_threadpool(encode_png, generated)
        except ValueError as exc:
            raise HTTPException(502, str(exc)) from exc
        output_name = f"{job.id}-output.png"
        await save_file(output_name, png)
    except Exception as exc:
        job.status = STATUS_FAILED
        job.error = (
            str(exc.detail)
            if isinstance(exc, HTTPException)
            else "Unexpected error during generation"
        )
        await db.commit()
        raise

    job.output_path = output_name
    job.status = STATUS_COMPLETED
    await db.commit()

    return serialize(job)


@router.get("/{job_id}", response_model=ImageJobOut)
async def get_job(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(ImageJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return serialize(job)
