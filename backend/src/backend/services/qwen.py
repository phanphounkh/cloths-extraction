"""Call the screenshot's Qwen Space through Gradio's queued HTTP API."""

import asyncio
import json
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from backend.core.config import settings
from backend.services.prompts import build_prompt

MAX_OUTPUT_BYTES = 30 * 1024 * 1024


def _check(response: httpx.Response) -> None:
    # Never expose upstream response bodies: they may contain credentials or
    # internal paths. The Space can also return HTML while starting up.
    if response.status_code in (401, 403):
        raise HTTPException(502, "Hugging Face denied access. Check HF_TOKEN and Space permissions.")
    if response.status_code == 429:
        raise HTTPException(503, "Hugging Face quota or rate limit reached. Try again later.")
    if response.is_error:
        raise HTTPException(502, "The Qwen Space is unavailable. It may be sleeping or restarting.")


def _arguments(info: dict, image_path: str, prompt: str) -> list:
    """Use the published input order/defaults, including all optional LoRA slots."""
    parameters = info["named_endpoints"][f"/{settings.hf_api_name}"]["parameters"]
    values = {
        "input_image": {"path": image_path, "meta": {"_type": "gradio.FileData"}},
        "prompt": prompt,
        "seed": 0,
        "randomize_seed": True,
        "guidance_scale": 1.0,
        "steps": 4,
    }
    if not {"input_image", "prompt"}.issubset({p["parameter_name"] for p in parameters}):
        raise ValueError("Unsupported Space input schema")
    arguments = []
    for parameter in parameters:
        name = parameter["parameter_name"]
        label = parameter.get("label", "").lower()
        if name in values:
            arguments.append(values[name])
        elif label.startswith("lora"):
            arguments.append("None")
        elif parameter.get("parameter_has_default"):
            arguments.append(parameter["parameter_default"])
        else:
            raise ValueError("Unsupported required Space parameter")
    return arguments


async def _result(client: httpx.AsyncClient, api: str, event_id: str) -> list:
    event = ""
    data: list[str] = []
    async with client.stream("GET", f"{api}/call/{settings.hf_api_name}/{quote(event_id, safe='')}") as response:
        _check(response)
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
            elif not line:
                if event == "error":
                    message = " ".join(data).lower()
                    if "quota" in message or "limit" in message:
                        raise HTTPException(503, "Hugging Face GPU quota reached. Try again later.")
                    raise HTTPException(502, "The Qwen Space could not generate an image. Try again.")
                if event == "complete":
                    result = json.loads("\n".join(data))
                    if not isinstance(result, list) or not result:
                        raise ValueError("Empty Space result")
                    return result
                event, data = "", []
    raise HTTPException(502, "The Qwen Space closed the connection before returning an image.")


async def generate_garment(image: bytes, garment: str, instruction: str) -> bytes:
    if not settings.ai_configured:
        raise HTTPException(503, "AI generation is not configured: set HF_TOKEN.")

    api = settings.hf_space_url.rstrip("/") + "/gradio_api"
    headers = {"Authorization": f"Bearer {settings.hf_token.get_secret_value()}"}
    try:
        # A wall-clock deadline also bounds a queue that keeps sending heartbeats.
        async with asyncio.timeout(settings.hf_timeout_seconds):
            async with httpx.AsyncClient(headers=headers, timeout=settings.hf_timeout_seconds) as client:
                response = await client.get(f"{api}/info")
                _check(response)
                info = response.json()
                # Validate the schema before uploading a user's photo.
                _arguments(info, "", "")

                response = await client.post(
                    f"{api}/upload", files={"files": ("input.jpg", image, "image/jpeg")}
                )
                _check(response)
                uploaded = response.json()
                if not isinstance(uploaded, list) or not uploaded or not isinstance(uploaded[0], str):
                    raise ValueError("Invalid upload response")
                arguments = _arguments(info, uploaded[0], build_prompt(garment, instruction))
                response = await client.post(f"{api}/call/{settings.hf_api_name}", json={"data": arguments})
                _check(response)
                event_id = response.json()["event_id"]
                if not isinstance(event_id, str) or not event_id:
                    raise ValueError("Invalid queue event")
                result = await _result(client, api, event_id)
                output_path = result[0]["path"]
                if not isinstance(output_path, str) or not output_path:
                    raise ValueError("Missing output image")

                # Build the file URL on our configured Space. Never forward the
                # token to a URL supplied in the model's response.
                async with client.stream("GET", f"{api}/file={quote(output_path, safe='/')}") as output:
                    _check(output)
                    chunks = bytearray()
                    async for chunk in output.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_OUTPUT_BYTES:
                            raise ValueError("Output image too large")
                    return bytes(chunks)
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise HTTPException(504, "Qwen image generation timed out. The GPU queue may be busy; try again.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Could not reach the Hugging Face Qwen Space.") from exc
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        raise HTTPException(502, "Unexpected response from the Qwen Space. Check HF_SPACE_URL and HF_API_NAME.") from exc
