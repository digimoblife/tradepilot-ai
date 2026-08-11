import io
import uuid
from PIL import Image, ImageDraw, ImageFont
from app.storage.image_compressor import compress_image_bytes, MAX_IMAGE_DIMENSION
from app.storage.local import LocalFileStorage


def _create_sample_image(width: int = 3000, height: int = 2000) -> bytes:
    """Create a large PNG image with text to test compression and readability."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw some text/lines simulating orderbook tables
    draw.rectangle([50, 50, width - 50, height - 50], outline=(0, 0, 0), width=5)
    draw.text((100, 100), "ORDERBOOK TEST - BBRI - 5250", fill=(0, 0, 0))
    draw.text((100, 300), "BID: 5225 | ASK: 5250 | VOL: 125000", fill=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_compress_large_image_reduces_size_and_limits_dimension() -> None:
    large_image = _create_sample_image(3000, 2000)
    original_size = len(large_image)

    compressed = compress_image_bytes(large_image, max_dimension=2048, quality=85)
    compressed_size = len(compressed)

    assert compressed_size < original_size

    # Verify compressed image is readable and valid PIL image
    with Image.open(io.BytesIO(compressed)) as img:
        w, h = img.size
        assert max(w, h) <= MAX_IMAGE_DIMENSION
        assert img.format in {"PNG", "JPEG", "WEBP"}


def test_compress_non_image_bytes_fallback_safely() -> None:
    raw_mock_bytes = b"mock-raw-binary-test-data"
    result = compress_image_bytes(raw_mock_bytes)
    assert result == raw_mock_bytes


def test_compress_empty_bytes() -> None:
    assert compress_image_bytes(b"") == b""


def test_local_storage_compresses_image_on_store(tmp_path) -> None:
    storage = LocalFileStorage(root=tmp_path)
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    large_image = _create_sample_image(2500, 1800)
    stored = storage.store(
        user_id=user_id,
        session_id=session_id,
        original_filename="large_orderbook.png",
        content=large_image,
    )

    assert stored.size_bytes < len(large_image)
    read_bytes = storage.read(file_reference=stored.file_reference)
    assert len(read_bytes) == stored.size_bytes

    # Ensure stored content can be opened as a valid image
    with Image.open(io.BytesIO(read_bytes)) as img:
        assert img.width <= MAX_IMAGE_DIMENSION
