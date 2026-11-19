import base64
import binascii
import logging

import httpx
from fastapi import HTTPException

from backend.core.config import settings

logger = logging.getLogger(__name__)

PROMPT = """\
Extract only the {garment} worn by the person in the reference photograph.

Create a realistic e-commerce product image.

Requirements:
- Show the garment alone.
- Remove the person completely.
- Remove the face, hands, and body.
- Remove the background.
- Use a plain white background.
- Preserve the garment's original color.
- Preserve fabric texture and stitching.
- Preserve visible logos and design details.
- Do not invent branding.
- Use a front-facing product view.
- Do not include a mannequin or hanger.
"""

# Friendlier messages for the OpenRouter status codes people hit most often.
UPSTREAM_ERRORS = {
    401: "OpenRouter rejected the API key. Check OPENROUTER_API_KEY.",
    402: "The OpenRouter account has insufficient credits.",
    403: "OpenRouter refused the request: the key's spend limit may be reached.",
    429: "OpenRouter rate limit reached. Try again in a moment.",
}


def build_prompt(garment: str, instruction: str) -> str:
    prompt = PROMPT.format(garment=garment)
    instruction = instruction.strip()
    if instruction:
        prompt += f"\nAdditional instructions:\n{instruction}\n"
    return prompt


def _upstream_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError):
        return response.text[:300]


async def generate_garment(image: bytes, garment: str, instruction: str) -> bytes:
    """Ask the image model for a product shot of the garment; return image bytes."""
    if not settings.openrouter_configured:
        raise HTTPException(503, "AI generation is not configured: set OPENROUTER_API_KEY.")

    data_url = "data:image/jpeg;base64," + base64.b64encode(image).decode()

    # OpenRouter's Image API serves every image model (Gemini, OpenAI
    # gpt-image, FLUX, ...); image-only models are not available through
    # /chat/completions.
    payload = {
        "model": settings.openrouter_model,
        "prompt": build_prompt(garment, instruction),
        "input_references": [{"type": "image_url", "image_url": {"url": data_url}}],
    }
    if settings.openrouter_image_quality:
        payload["quality"] = settings.openrouter_image_quality

    try:
        async with httpx.AsyncClient(timeout=settings.openrouter_timeout_seconds) as client:
            response = await client.post(
                f"{settings.openrouter_base_url}/images",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Image generation timed out. Try again.") from exc
    except httpx.HTTPError as exc:
        logger.exception("Could not reach OpenRouter")
        raise HTTPException(502, "Could not reach the image generation service.") from exc

    if response.is_error:
        message = _upstream_message(response)
        logger.warning("OpenRouter returned %s: %s", response.status_code, message)
        detail = UPSTREAM_ERRORS.get(
            response.status_code,
            f"Image generation failed ({response.status_code}): {message}",
        )
        raise HTTPException(502, detail)

    try:
        images = response.json().get("data") or []
    except (ValueError, AttributeError) as exc:
        raise HTTPException(502, "Unexpected response from the image model.") from exc

    if not images:
        raise HTTPException(502, "The model did not return an image.")

    try:
        return base64.b64decode(images[0]["b64_json"], validate=True)
    except (KeyError, IndexError, TypeError, binascii.Error) as exc:
        raise HTTPException(502, "The model returned an unreadable image.") from exc
