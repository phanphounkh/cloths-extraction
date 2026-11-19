import logging

import httpx
from fastapi import HTTPException

from backend.core.config import settings

logger = logging.getLogger(__name__)


def _upstream_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["detail"])[:300]
    except (ValueError, KeyError, TypeError):
        return response.text[:300]


async def generate_garment_on_kaggle(image: bytes, garment: str, instruction: str) -> bytes:
    """Send the photo to the Kaggle GPU server; return the generated PNG bytes."""
    if not settings.kaggle_configured:
        raise HTTPException(503, "AI generation is not configured: set KAGGLE_BASE_URL and KAGGLE_API_TOKEN.")

    url = settings.kaggle_base_url.rstrip("/") + "/generate"
    try:
        async with httpx.AsyncClient(timeout=settings.kaggle_timeout_seconds) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.kaggle_api_token}"},
                files={"image": ("input.jpg", image, "image/jpeg")},
                # The segmentation server extracts by garment type; free-text
                # instructions only apply to the OpenRouter generator.
                data={"garment": garment},
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "GPU generation timed out. The Kaggle notebook may be busy or stopped.") from exc
    except httpx.HTTPError as exc:
        logger.exception("Could not reach the Kaggle GPU server")
        raise HTTPException(
            502, "Could not reach the Kaggle GPU server. Is the notebook still running?"
        ) from exc

    if response.status_code == 401:
        raise HTTPException(502, "The Kaggle GPU server rejected the token. Check KAGGLE_API_TOKEN.")
    if response.is_error:
        message = _upstream_message(response)
        logger.warning("Kaggle GPU server returned %s: %s", response.status_code, message)
        raise HTTPException(502, f"GPU generation failed ({response.status_code}): {message}")

    if not response.content:
        raise HTTPException(502, "The GPU server returned an empty image.")
    return response.content
