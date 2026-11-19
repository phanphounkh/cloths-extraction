from io import BytesIO

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000


def _to_rgb(image: Image.Image) -> Image.Image:
    """Convert to RGB, putting transparent areas on white instead of black."""
    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if not has_alpha:
        return image.convert("RGB")

    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def _open_checked(data: bytes) -> Image.Image:
    """Open and fully decode an image, refusing oversized dimensions."""
    with Image.open(BytesIO(data)) as source:
        if source.width * source.height > MAX_PIXELS:
            raise HTTPException(413, "Image dimensions are too large")
        source.load()
        # Phone photos are often stored sideways with an EXIF rotation flag.
        # exif_transpose returns a new image, so `source` can be closed.
        return ImageOps.exif_transpose(source)


def normalize_upload(data: bytes) -> bytes:
    """Validate an uploaded photo and re-encode it as a clean RGB JPEG.

    Re-encoding strips metadata (including GPS location) and anything that
    is not image data.
    """
    if not data:
        raise HTTPException(422, "Empty image")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image exceeds 10 MB")

    try:
        with _open_checked(data) as image:
            output = BytesIO()
            _to_rgb(image).save(output, format="JPEG", quality=90)
            return output.getvalue()
    except Image.DecompressionBombError as exc:
        raise HTTPException(413, "Image dimensions are too large") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(422, "Invalid image file") from exc


def encode_png(data: bytes) -> bytes:
    """Validate an image produced by the model and encode it as PNG.

    Raises ValueError if the bytes are not a usable image.
    """
    try:
        with _open_checked(data) as image:
            output = BytesIO()
            _to_rgb(image).save(output, format="PNG", optimize=True)
            return output.getvalue()
    except (HTTPException, Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
        raise ValueError("Model returned an invalid image") from exc
