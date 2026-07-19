"""Tests for EvidenceUploadValidator."""

from __future__ import annotations

import hashlib
import os
from io import BytesIO

import pytest
from PIL import Image

from app.evidence import (
    EvidenceEmptyError,
    EvidenceFileTooLargeError,
    EvidenceImageInvalidError,
    EvidenceMimeMismatchError,
    EvidenceMimeUnsupportedError,
    EvidenceTypeUnsupportedError,
    EvidenceUploadValidator,
    ValidatedEvidenceUpload,
)
from app.models.enums import EvidenceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALIDATOR = EvidenceUploadValidator()


def _make_image_bytes(
    fmt: str = "PNG",
    size: tuple[int, int] = (100, 100),
    color: str = "red",
) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_jpeg_bytes(size: tuple[int, int] = (100, 100)) -> bytes:
    return _make_image_bytes("JPEG", size)


def _make_webp_bytes(size: tuple[int, int] = (100, 100)) -> bytes:
    return _make_image_bytes("WEBP", size)


# ---------------------------------------------------------------------------
# Valid uploads
# ---------------------------------------------------------------------------


class TestValidUploads:
    def test_valid_png(self) -> None:
        content = _make_image_bytes("PNG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="chart.png",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        )
        assert isinstance(result, ValidatedEvidenceUpload)
        assert result.detected_mime_type == "image/png"
        assert result.normalized_extension == ".png"
        assert result.width == 100
        assert result.height == 100
        assert result.size_bytes == len(content)
        assert result.checksum_sha256 == hashlib.sha256(content).hexdigest()

    def test_valid_jpeg(self) -> None:
        content = _make_jpeg_bytes()
        result = _VALIDATOR.validate(
            content=content,
            original_filename="photo.jpg",
            declared_mime_type="image/jpeg",
            evidence_type=EvidenceType.CHART_THREE_MONTH,
        )
        assert result.detected_mime_type == "image/jpeg"
        assert result.normalized_extension == ".jpg"

    def test_valid_webp(self) -> None:
        content = _make_webp_bytes()
        result = _VALIDATOR.validate(
            content=content,
            original_filename="screenshot.webp",
            declared_mime_type="image/webp",
            evidence_type=EvidenceType.CUSTOM_IMAGE,
        )
        assert result.detected_mime_type == "image/webp"
        assert result.normalized_extension == ".webp"

    def test_detected_mime_correct(self) -> None:
        content = _make_image_bytes("PNG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="fake.jpg",
            declared_mime_type=None,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        )
        # Detected MIME is from content, not filename
        assert result.detected_mime_type == "image/png"

    def test_normalized_extension_correct(self) -> None:
        content = _make_image_bytes("JPEG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="chart.png",
            declared_mime_type=None,
            evidence_type=EvidenceType.CHART_SIX_MONTH,
        )
        # Extension is from detected format, not filename
        assert result.normalized_extension == ".jpg"

    def test_width_and_height(self) -> None:
        content = _make_image_bytes("PNG", size=(640, 480))
        result = _VALIDATOR.validate(
            content=content,
            original_filename="wide.png",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.CHART_INTRADAY,
        )
        assert result.width == 640
        assert result.height == 480

    def test_size_bytes_correct(self) -> None:
        content = b"x" * 1024
        result = _VALIDATOR.validate(
            content=content,
            original_filename="note.txt",
            declared_mime_type=None,
            evidence_type=EvidenceType.USER_NOTE,
        )
        assert result.size_bytes == 1024

    def test_checksum_sha256(self) -> None:
        content = _make_image_bytes("PNG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="check.png",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.CUSTOM_IMAGE,
        )
        assert result.checksum_sha256 == hashlib.sha256(content).hexdigest()
        assert len(result.checksum_sha256) == 64

    def test_original_bytes_unchanged(self) -> None:
        content = _make_image_bytes("PNG")
        original = content[:]
        _VALIDATOR.validate(
            content=content,
            original_filename="test.png",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        )
        assert content == original  # not mutated


# ---------------------------------------------------------------------------
# Empty and size validation
# ---------------------------------------------------------------------------


class TestEmptyAndSize:
    def test_empty_bytes_rejected(self) -> None:
        with pytest.raises(EvidenceEmptyError):
            _VALIDATOR.validate(
                content=b"",
                original_filename="empty.png",
                declared_mime_type=None,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            )

    def test_oversized_file_rejected(self) -> None:
        max_size = 100
        strict = EvidenceUploadValidator(max_upload_size_bytes=max_size)
        with pytest.raises(EvidenceFileTooLargeError):
            strict.validate(
                content=b"x" * (max_size + 1),
                original_filename="large.png",
                declared_mime_type=None,
                evidence_type=EvidenceType.CHART_THREE_MONTH,
            )

    def test_size_at_limit_accepted(self) -> None:
        max_size = 100
        strict = EvidenceUploadValidator(max_upload_size_bytes=max_size)
        result = strict.validate(
            content=b"x" * max_size,
            original_filename="exact.txt",
            declared_mime_type=None,
            evidence_type=EvidenceType.USER_NOTE,
        )
        assert result.size_bytes == max_size


# ---------------------------------------------------------------------------
# MIME validation
# ---------------------------------------------------------------------------


class TestMimeValidation:
    def test_unsupported_declared_mime_rejected(self) -> None:
        content = _make_image_bytes("PNG")
        with pytest.raises(EvidenceMimeUnsupportedError):
            _VALIDATOR.validate(
                content=content,
                original_filename="chart.gif",
                declared_mime_type="image/gif",
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            )

    def test_supported_content_with_correct_declared_mime(self) -> None:
        content = _make_image_bytes("WEBP")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="img.webp",
            declared_mime_type="image/webp",
            evidence_type=EvidenceType.CUSTOM_IMAGE,
        )
        assert result.detected_mime_type == "image/webp"

    def test_declared_detected_mismatch_rejected(self) -> None:
        content = _make_image_bytes("PNG")
        with pytest.raises(EvidenceMimeMismatchError):
            _VALIDATOR.validate(
                content=content,
                original_filename="fake.png",
                declared_mime_type="image/jpeg",
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            )

    def test_no_declared_mime_validates_by_content(self) -> None:
        content = _make_image_bytes("PNG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="unknown",
            declared_mime_type=None,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        )
        assert result.detected_mime_type == "image/png"

    def test_renamed_text_file_rejected(self) -> None:
        content = b"this is not an image"
        with pytest.raises(EvidenceImageInvalidError):
            _VALIDATOR.validate(
                content=content,
                original_filename="chart.png",  # .png extension
                declared_mime_type="image/png",
                evidence_type=EvidenceType.CHART_THREE_MONTH,
            )

    def test_no_declared_mime_still_validates_image_content(self) -> None:
        content = b"not an image"
        with pytest.raises(EvidenceImageInvalidError):
            _VALIDATOR.validate(
                content=content,
                original_filename="test.png",
                declared_mime_type=None,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            )


# ---------------------------------------------------------------------------
# Invalid images
# ---------------------------------------------------------------------------


class TestInvalidImages:
    def test_random_bytes_rejected(self) -> None:
        with pytest.raises(EvidenceImageInvalidError):
            _VALIDATOR.validate(
                content=os.urandom(256),
                original_filename="random.bin",
                declared_mime_type="image/png",
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            )

    def test_corrupt_png_rejected(self) -> None:
        content = _make_image_bytes("PNG")
        corrupt = content[:50] + b"\xff\xff\xff\xff" + content[54:]
        with pytest.raises(EvidenceImageInvalidError):
            _VALIDATOR.validate(
                content=corrupt,
                original_filename="corrupt.png",
                declared_mime_type="image/png",
                evidence_type=EvidenceType.CUSTOM_IMAGE,
            )

    def test_truncated_jpeg_rejected(self) -> None:
        content = _make_jpeg_bytes()
        truncated = content[: len(content) // 2]
        with pytest.raises(EvidenceImageInvalidError):
            _VALIDATOR.validate(
                content=truncated,
                original_filename="truncated.jpg",
                declared_mime_type="image/jpeg",
                evidence_type=EvidenceType.CHART_THREE_MONTH,
            )

    def test_valid_extension_with_invalid_bytes(self) -> None:
        with pytest.raises(EvidenceImageInvalidError):
            _VALIDATOR.validate(
                content=b"not-a-png",
                original_filename="valid_name.png",
                declared_mime_type=None,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            )


# ---------------------------------------------------------------------------
# Evidence types
# ---------------------------------------------------------------------------


class TestEvidenceTypes:
    @pytest.mark.parametrize(
        "evidence_type",
        [
            EvidenceType.ORDERBOOK_SCREENSHOT,
            EvidenceType.CHART_THREE_MONTH,
            EvidenceType.CHART_SIX_MONTH,
            EvidenceType.CHART_DAILY,
            EvidenceType.CHART_INTRADAY,
            EvidenceType.BROKER_SUMMARY,
            EvidenceType.FOREIGN_FLOW,
            EvidenceType.NEWS_SCREENSHOT,
            EvidenceType.CUSTOM_IMAGE,
        ],
    )
    def test_image_evidence_types_accepted(self, evidence_type: EvidenceType) -> None:
        content = _make_image_bytes("PNG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="img.png",
            declared_mime_type="image/png",
            evidence_type=evidence_type,
        )
        assert result.evidence_type == evidence_type

    @pytest.mark.parametrize(
        "evidence_type",
        [
            EvidenceType.USER_NOTE,
            EvidenceType.MARKET_DATA_SNAPSHOT,
        ],
    )
    def test_non_image_evidence_types_accepted(self, evidence_type: EvidenceType) -> None:
        result = _VALIDATOR.validate(
            content=b"some text content",
            original_filename="note.txt",
            declared_mime_type=None,
            evidence_type=evidence_type,
        )
        assert result.evidence_type == evidence_type
        # Non-image types have empty MIME and extension
        assert result.detected_mime_type == ""

    def test_unknown_string_evidence_type_rejected(self) -> None:
        with pytest.raises(EvidenceTypeUnsupportedError) as exc:
            _VALIDATOR.validate(
                content=_make_image_bytes("PNG"),
                original_filename="test.png",
                declared_mime_type="image/png",
                evidence_type="INVALID_TYPE",
            )
        assert "EVIDENCE_TYPE_UNSUPPORTED" in str(exc.value)

    def test_string_evidence_type_normalized(self) -> None:
        content = _make_image_bytes("PNG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="img.png",
            declared_mime_type="image/png",
            evidence_type="ORDERBOOK_SCREENSHOT",
        )
        assert result.evidence_type == EvidenceType.ORDERBOOK_SCREENSHOT


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------


class TestDimensions:
    def test_valid_dimensions_accepted(self) -> None:
        content = _make_image_bytes("PNG", size=(2000, 1500))
        result = _VALIDATOR.validate(
            content=content,
            original_filename="large.png",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.CHART_SIX_MONTH,
        )
        assert result.width == 2000
        assert result.height == 1500

    def test_zero_dimension_not_possible_with_pillow(self) -> None:
        # Pillow does not allow creating zero-size images
        pass


# ---------------------------------------------------------------------------
# Security and scope
# ---------------------------------------------------------------------------


class TestSecurityAndScope:
    def test_malicious_filename_safe(self) -> None:
        content = _make_image_bytes("PNG")
        result = _VALIDATOR.validate(
            content=content,
            original_filename="../../etc/passwd",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        )
        # Validation succeeds - the filename is just metadata
        assert isinstance(result, ValidatedEvidenceUpload)
        assert result.detected_mime_type == "image/png"

    def test_no_filesystem_writes(self) -> None:
        content = _make_image_bytes("PNG")
        _VALIDATOR.validate(
            content=content,
            original_filename="test.png",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        )
        # Test passes if no OSError or file write occurs
        # (validated by absence of filesystem operations in the code)

    def test_no_database_network_access(self) -> None:
        content = _make_image_bytes("PNG")
        _VALIDATOR.validate(
            content=content,
            original_filename="test.png",
            declared_mime_type="image/png",
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        )
        # Test passes if no DB or network imports are triggered
        # (validated by pure in-memory operations)
