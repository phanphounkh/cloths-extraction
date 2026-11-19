"""GPU clothing product-photo server for the SAB backend, meant to run in a Kaggle notebook.

Pipeline for POST /generate (the garment design always comes from the original photo):
  1. Segmentation: SegFormer finds the requested garment and its mask. The mask is cleaned
     (specks removed, small holes filled, only the main garment pieces kept).
  2. Keep the original pixels: the visible garment is placed on a white square canvas, unchanged.
  3. Generate only the hidden areas: a Stable Diffusion inpainting model fills the holes behind
     the body/hair/bags and a thin band at the garment edge. Original garment pixels are never
     repainted.
  4. Design check: the result is accepted only if
       - the rebuilt area is not too large compared with the visible garment,
       - the rebuilt colour matches the visible garment,
       - SegFormer still finds the same garment shape in the result.
     If a check fails, the server returns the original-pixels cutout (no generated pixels) and
     sets the X-Needs-Review header with the reasons, so the result is flagged for review.

    GET  /health    -> {"status": "ok", ...}
    POST /generate  -> multipart fields `image` (JPEG) and `garment` (optional),
                       header `Authorization: Bearer <GPU_SERVER_TOKEN>`;
                       responds with the product image as PNG. Headers:
                       X-Needs-Review: 0 or 1; X-Review-Reasons: text when 1.
"""

import asyncio
import io
import os
import secrets
import threading

import numpy as np
import torch
from diffusers import StableDiffusionInpaintPipeline
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps
from scipy import ndimage
from transformers import AutoImageProcessor, SegformerForSemanticSegmentation

SEG_MODEL_ID = os.environ.get("MODEL_ID", "mattmdjaga/segformer_b2_clothes")
INPAINT_MODEL_ID = os.environ.get("INPAINT_MODEL_ID", "stable-diffusion-v1-5/stable-diffusion-inpainting")
TOKEN = os.environ.get("GPU_SERVER_TOKEN", "")
INPAINT_STEPS = int(os.environ.get("INPAINT_STEPS", "25"))
# Width (px, on the 512 canvas) of the band just outside the garment that may be repainted.
EDGE_PX = int(os.environ.get("EDGE_PX", "12"))
# Design-check thresholds (tune after testing on real photos).
MAX_REBUILT_RATIO = float(os.environ.get("MAX_REBUILT_RATIO", "0.35"))
MAX_COLOR_DIFF = float(os.environ.get("MAX_COLOR_DIFF", "30"))
MIN_RESEG_IOU = float(os.environ.get("MIN_RESEG_IOU", "0.75"))

CANVAS = 512
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Label ids from the segmentation model's config (id2label), per garment type.
GARMENT_LABELS = {
    "shirt": [4],  # Upper-clothes
    "jacket": [4],  # Upper-clothes
    "dress": [7],  # Dress
    "pants": [6],  # Pants
    "skirt": [5],  # Skirt
    "shoes": [9, 10],  # Left-shoe, Right-shoe
    "other": [4, 5, 6, 7, 8, 9, 10, 17],  # any clothing-like item
}

GARMENT_NAMES = {
    "shirt": "shirt",
    "jacket": "jacket",
    "dress": "dress",
    "pants": "pair of pants",
    "skirt": "skirt",
    "shoes": "pair of shoes",
    "other": "clothing item",
}

if not TOKEN:
    raise RuntimeError("Set GPU_SERVER_TOKEN before starting the server.")
if not torch.cuda.is_available():
    raise RuntimeError("No GPU found. In Kaggle, enable an accelerator (GPU T4 x2).")

print(f"Loading {SEG_MODEL_ID} ...", flush=True)
seg_processor = AutoImageProcessor.from_pretrained(SEG_MODEL_ID)
seg_model = SegformerForSemanticSegmentation.from_pretrained(SEG_MODEL_ID).eval().to("cuda")

print(f"Loading {INPAINT_MODEL_ID} ...", flush=True)
inpaint = StableDiffusionInpaintPipeline.from_pretrained(
    INPAINT_MODEL_ID,
    torch_dtype=torch.float16,
    variant="fp16",
    safety_checker=None,
    requires_safety_checker=False,
).to("cuda")
print("Models ready.", flush=True)

app = FastAPI(title="SAB GPU clothing server")
_gpu_lock = threading.Lock()


def _segment(image: Image.Image, garment: str) -> np.ndarray:
    """Return a boolean mask of the requested garment at the image's size."""
    with torch.no_grad():
        inputs = seg_processor(images=image, return_tensors="pt").to("cuda")
        logits = seg_model(**inputs).logits
        logits = torch.nn.functional.interpolate(
            logits, size=image.size[::-1], mode="bilinear", align_corners=False
        )
        labels = logits.argmax(dim=1)[0].cpu().numpy()
    return np.isin(labels, GARMENT_LABELS[garment])


def _disk(radius: int) -> np.ndarray:
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    return x * x + y * y <= radius * radius


def _clean_mask(mask: np.ndarray) -> np.ndarray:
    """Remove specks, thin strands and narrow parts such as ties, keep only the main garment pieces."""
    # Opening with a disk wider than a tie removes the tie, but keeps sleeves and the body.
    radius = max(5, round(0.03 * max(mask.shape)))
    mask = ndimage.binary_opening(mask, structure=_disk(radius))
    labels, count = ndimage.label(mask)
    if count == 0:
        return mask
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    # Keep pieces that are at least 5% of the largest one (e.g. both sleeves), drop the rest.
    keep = np.where(sizes >= 0.05 * sizes.max())[0] + 1
    return ndimage.binary_fill_holes(np.isin(labels, keep))


def _refine_edges(rgb: np.ndarray, mask: np.ndarray) -> Image.Image:
    """Smooth the outline, replace background colour at the edge, and soften the edge on white."""
    smooth = ndimage.gaussian_filter(mask.astype(np.float32), sigma=2.0) > 0.5
    smooth = ndimage.binary_erosion(smooth, iterations=1)  # trim a 1 px background fringe
    inner = ndimage.binary_erosion(smooth, iterations=6)
    edge = smooth & ~inner
    # Edge pixels take the colour of the nearest interior garment pixel.
    _, idx = ndimage.distance_transform_edt(~inner, return_indices=True)
    colours = rgb.astype(np.float32).copy()
    colours[edge] = rgb[idx[0][edge], idx[1][edge]]
    alpha = ndimage.gaussian_filter(smooth.astype(np.float32), sigma=0.7)[..., None]
    out = colours * alpha + 255.0 * (1.0 - alpha)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def _place_on_canvas(source: Image.Image, mask: np.ndarray) -> tuple[Image.Image, np.ndarray]:
    """Crop to the garment (with a margin), scale to fit, and centre it on a white square canvas.

    Returns the canvas image and the garment mask at canvas size. Pixels are copied, not generated.
    """
    ys, xs = np.where(mask)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    pad = int(0.1 * max(x1 - x0, y1 - y0))
    box = (max(0, x0 - pad), max(0, y0 - pad), min(source.width, x1 + pad), min(source.height, y1 + pad))
    crop = source.crop(box)
    crop_mask = mask[box[1]:box[3], box[0]:box[2]]

    limit = int(CANVAS * 0.85)
    scale = min(limit / crop.width, limit / crop.height)
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    crop = crop.resize(size, Image.LANCZOS)
    crop_mask = np.array(
        Image.fromarray((crop_mask * 255).astype(np.uint8)).resize(size, Image.NEAREST)
    ) > 127

    offset = ((CANVAS - size[0]) // 2, (CANVAS - size[1]) // 2)
    canvas = Image.new("RGB", (CANVAS, CANVAS), (255, 255, 255))
    canvas.paste(crop, offset)
    canvas_mask = np.zeros((CANVAS, CANVAS), dtype=bool)
    canvas_mask[offset[1]:offset[1] + size[1], offset[0]:offset[0] + size[0]] = crop_mask
    return canvas, canvas_mask


PALETTE = {
    "white": (245, 245, 245),
    "off-white": (235, 228, 215),
    "beige": (220, 200, 170),
    "cream": (240, 230, 200),
    "brown": (120, 85, 60),
    "grey": (128, 128, 128),
    "black": (25, 25, 25),
    "navy": (30, 40, 80),
    "blue": (60, 100, 170),
    "green": (60, 110, 60),
    "olive green": (90, 100, 50),
    "red": (170, 40, 40),
    "pink": (230, 170, 180),
    "yellow": (230, 200, 80),
    "orange": (220, 120, 50),
    "purple": (110, 70, 130),
}


def _colour_name(rgb: np.ndarray) -> str:
    """Nearest named colour from a small palette, used to describe the garment in the prompt."""
    return min(PALETTE, key=lambda name: float(np.sum((np.array(PALETTE[name]) - rgb) ** 2)))


def _build_prompt(garment: str, colour: str) -> str:
    name = GARMENT_NAMES[garment]
    return (
        f"professional product photo of a {colour} {name}, plain white background, studio lighting, "
        "realistic fabric texture, same colour and design as the original garment"
    )


NEGATIVE_PROMPT = "person, human, skin, hands, arms, hair, face, mannequin, hanger, text, new logo, shadow"


def _extract_product(source: Image.Image, garment: str) -> tuple[Image.Image, list[str]]:
    with _gpu_lock:
        mask = _segment(source, garment)
        if not mask.any():
            raise ValueError(f"No {GARMENT_NAMES[garment]} found in the photo.")

        mask = _clean_mask(mask)
        if not mask.any():
            raise ValueError(f"No clear {GARMENT_NAMES[garment]} found in the photo.")

        # 1-2. Original garment pixels on a white canvas.
        canvas, garment_mask = _place_on_canvas(source, mask)
        photo = np.asarray(canvas).copy()
        visible = photo.copy()
        visible[~garment_mask] = 255

        # 3. Area to rebuild: holes inside the garment silhouette, plus a thin band at its edge.
        # Wide closing fills the slit left where the tie was removed, not only enclosed holes.
        silhouette = ndimage.binary_closing(garment_mask, iterations=24)
        holes = silhouette & ~garment_mask
        band = ndimage.binary_dilation(garment_mask, iterations=EDGE_PX) & ~garment_mask
        repaint = holes | band

        # Start the fill from the garment's average colour so the model keeps the colour.
        # The edge band stays white, so the garment colour does not spread onto the background.
        garment_pixels = photo[ndimage.binary_erosion(garment_mask, iterations=8)]
        fill_rgb = garment_pixels.mean(axis=0) if garment_pixels.size else np.array([200.0, 200.0, 200.0])
        colour = _colour_name(fill_rgb)
        init = visible.copy()
        init[holes] = fill_rgb.astype(np.uint8)

        generated = np.asarray(
            inpaint(
                prompt=_build_prompt(garment, colour),
                negative_prompt=NEGATIVE_PROMPT,
                image=Image.fromarray(init),
                mask_image=Image.fromarray((repaint * 255).astype(np.uint8)),
                num_inference_steps=INPAINT_STEPS,
                guidance_scale=7.5,
                generator=torch.Generator("cpu").manual_seed(0),
            ).images[0].convert("RGB")
        ).copy()

        # Only the rebuilt pixels come from the model; the garment keeps its original pixels.
        final = visible.copy()
        final[repaint] = generated[repaint]

        # 4. Design check.
        reasons: list[str] = []
        garment_area = int(garment_mask.sum())
        rebuilt_ratio = float(repaint.sum()) / max(1, garment_area)
        if rebuilt_ratio > MAX_REBUILT_RATIO:
            reasons.append(f"too much hidden area was rebuilt ({rebuilt_ratio:.0%} of the garment)")

        colour_diff = 0.0
        if holes.sum() > 200:
            original_mean = fill_rgb
            rebuilt_mean = final[holes].mean(axis=0)
            colour_diff = float(np.abs(original_mean - rebuilt_mean).max())
            if colour_diff > MAX_COLOR_DIFF:
                reasons.append(f"rebuilt colour differs from the garment (difference {colour_diff:.0f})")

        reseg = _segment(Image.fromarray(final), garment)
        union = int((reseg | garment_mask).sum())
        iou = float((reseg & garment_mask).sum()) / max(1, union)
        if iou < MIN_RESEG_IOU:
            reasons.append(f"garment shape changed after rebuilding (overlap {iou:.0%})")

    print(
        f"[design check] {garment} ({colour}): rebuilt {rebuilt_ratio:.0%}, colour diff {colour_diff:.0f}, "
        f"shape overlap {iou:.0%} -> {'passed' if not reasons else 'FLAGGED: ' + '; '.join(reasons)}",
        flush=True,
    )
    if reasons:
        # Fall back to the original pixels only: nothing invented, flagged for review.
        return _refine_edges(visible, garment_mask), reasons
    # Output = visible garment plus any repainted holes. The edge band is context only, so it is dropped.
    return _refine_edges(final, garment_mask | holes), reasons


@app.get("/health")
def health():
    return {"status": "ok", "segmentation_model": SEG_MODEL_ID, "inpaint_model": INPAINT_MODEL_ID}


@app.post("/generate")
async def generate(
    image: UploadFile = File(...),
    garment: str = Form("other"),
    authorization: str | None = Header(default=None),
):
    if not authorization or not secrets.compare_digest(authorization, f"Bearer {TOKEN}"):
        raise HTTPException(401, "Invalid or missing token.")
    if garment not in GARMENT_LABELS:
        raise HTTPException(400, f"Unknown garment: {garment}")

    raw = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image is too large.")
    try:
        source = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, "Could not read the image.") from exc

    try:
        result, reasons = await asyncio.to_thread(_extract_product, source, garment)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        raise HTTPException(503, "GPU ran out of memory. Try a smaller image.")

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    headers = {"X-Needs-Review": "1" if reasons else "0"}
    if reasons:
        headers["X-Review-Reasons"] = "; ".join(reasons)[:400]
    return Response(content=buffer.getvalue(), media_type="image/png", headers=headers)
