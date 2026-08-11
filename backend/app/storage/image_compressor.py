"""Image compression utility for evidence uploads (preserving AI vision readability)."""

from __future__ import annotations

import io
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_DIMENSION = 2048
DEFAULT_QUALITY = 85


def compress_image_bytes(
    content: bytes,
    *,
    max_dimension: int = MAX_IMAGE_DIMENSION,
    quality: int = DEFAULT_QUALITY,
) -> bytes:
    """Compress image bytes if valid image content.

    Resizes high-resolution images down to max_dimension using LANCZOS filter,
    and encodes with high quality (85) to preserve text sharpness for AI model.
    Returns original content if not a valid decodeable image or if compression
    fails/does not reduce size.
    """
    if not content:
        return content

    try:
        with Image.open(io.BytesIO(content)) as img:
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG", "JPG", "WEBP", "BMP", "TIFF"}:
                return content

            width, height = img.size
            if width <= 0 or height <= 0:
                return content

            needs_resize = width > max_dimension or height > max_dimension

            # Use LANCZOS filter for optimal text sharpness when downscaling
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS

            image_to_process = img
            if needs_resize:
                image_to_process = img.copy()
                image_to_process.thumbnail((max_dimension, max_dimension), resample_filter)

            out_format = fmt if fmt in {"JPEG", "JPG", "WEBP", "PNG"} else "JPEG"

            save_kwargs: dict[str, object] = {}
            if out_format in {"JPEG", "JPG"}:
                if image_to_process.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", image_to_process.size, (255, 255, 255))
                    if image_to_process.mode == "RGBA":
                        bg.paste(image_to_process, mask=image_to_process.split()[3])
                    else:
                        bg.paste(image_to_process.convert("RGB"))
                    image_to_process = bg
                elif image_to_process.mode != "RGB":
                    image_to_process = image_to_process.convert("RGB")
                save_kwargs = {"quality": quality, "optimize": True}
            elif out_format == "WEBP":
                save_kwargs = {"quality": quality, "method": 6}
            elif out_format == "PNG":
                save_kwargs = {"optimize": True}

            buf = io.BytesIO()
            image_to_process.save(buf, format=out_format, **save_kwargs)
            compressed_bytes = buf.getvalue()

            if compressed_bytes and len(compressed_bytes) < len(content):
                return compressed_bytes
            return content
    except (UnidentifiedImageError, OSError, Exception):
        return content
