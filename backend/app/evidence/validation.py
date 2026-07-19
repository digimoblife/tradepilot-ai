"""Evidence upload validation service (TP-0602).

Validates uploaded evidence files before storage or database persistence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.models.enums import EvidenceType

# ---------------------------------------------------------------------------
# Canonical constants
# ---------------------------------------------------------------------------

SUPPORTED_IMAGE_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
    }
)

IMAGE_EVIDENCE_TYPES: frozenset[EvidenceType] = frozenset(
    {
        EvidenceType.ORDERBOOK_SCREENSHOT,
        EvidenceType.CHART_THREE_MONTH,
        EvidenceType.CHART_SIX_MONTH,
        EvidenceType.CHART_DAILY,
        EvidenceType.CHART_INTRADAY,
        EvidenceType.BROKER_SUMMARY,
        EvidenceType.FOREIGN_FLOW,
        EvidenceType.NEWS_SCREENSHOT,
        EvidenceType.CUSTOM_IMAGE,
    }
)

NON_IMAGE_EVIDENCE_TYPES: frozenset[EvidenceType] = frozenset(
    {
        EvidenceType.USER_NOTE,
        EvidenceType.MARKET_DATA_SNAPSHOT,
    }
)

ALL_EVIDENCE_TYPES: frozenset[EvidenceType] = frozenset(EvidenceType)

PIL_FORMAT_TO_EXTENSION: dict[str, str] = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
}

PIL_FORMAT_TO_MIME: dict[str, str] = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}

# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidatedEvidenceUpload:
    """Immutable result of a successful evidence upload validation."""

    evidence_type: EvidenceType
    detected_mime_type: str
    normalized_extension: str
    size_bytes: int
    checksum_sha256: str
    width: int = 0
    height: int = 0


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class EvidenceValidationError(Exception):
    """Base exception for all evidence validation errors."""

    code: str = "EVIDENCE_VALIDATION_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class EvidenceEmptyError(EvidenceValidationError):
    """Raised when upload content is empty or missing."""

    code: str = "EVIDENCE_EMPTY_FILE"


class EvidenceFileTooLargeError(EvidenceValidationError):
    """Raised when upload exceeds the maximum allowed size."""

    code: str = "EVIDENCE_FILE_TOO_LARGE"


class EvidenceTypeUnsupportedError(EvidenceValidationError):
    """Raised when the evidence type is not a canonical value."""

    code: str = "EVIDENCE_TYPE_UNSUPPORTED"


class EvidenceMimeUnsupportedError(EvidenceValidationError):
    """Raised when the MIME type is not a supported image format."""

    code: str = "EVIDENCE_MIME_UNSUPPORTED"


class EvidenceMimeMismatchError(EvidenceValidationError):
    """Raised when declared MIME type does not match detected content."""

    code: str = "EVIDENCE_MIME_MISMATCH"


class EvidenceImageInvalidError(EvidenceValidationError):
    """Raised when image content cannot be decoded or is corrupt."""

    code: str = "EVIDENCE_IMAGE_INVALID"


class EvidenceDimensionsInvalidError(EvidenceValidationError):
    """Raised when image dimensions are non-positive."""

    code: str = "EVIDENCE_DIMENSIONS_INVALID"


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class EvidenceUploadValidator:
    """Validates evidence uploads before storage.

    Checks evidence type, file size, MIME type, image content,
    dimensions, and calculates a SHA-256 checksum.
    """

    def __init__(self, max_upload_size_bytes: int = 10485760) -> None:
        self._max_size = max_upload_size_bytes

    def validate(
        self,
        *,
        content: bytes,
        original_filename: str,
        declared_mime_type: str | None,
        evidence_type: EvidenceType | str,
    ) -> ValidatedEvidenceUpload:
        """Validate an evidence upload and return validated metadata.

        Raises ``EvidenceValidationError`` (or a subclass) on failure.
        Does not store the file or access the database.
        """
        normalized_type = self._normalize_evidence_type(evidence_type)

        self._check_empty(content)
        self._check_size(content)

        checksum = hashlib.sha256(content).hexdigest()

        if normalized_type in IMAGE_EVIDENCE_TYPES:
            return self._validate_image(
                content=content,
                declared_mime_type=declared_mime_type,
                evidence_type=normalized_type,
                checksum=checksum,
            )

        return ValidatedEvidenceUpload(
            evidence_type=normalized_type,
            detected_mime_type="",
            normalized_extension="",
            size_bytes=len(content),
            checksum_sha256=checksum,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_evidence_type(
        evidence_type: EvidenceType | str,
    ) -> EvidenceType:
        if isinstance(evidence_type, EvidenceType):
            return evidence_type
        try:
            return EvidenceType(evidence_type)
        except ValueError:
            raise EvidenceTypeUnsupportedError(
                message=f"Unrecognised evidence type: {evidence_type}",
            )

    @staticmethod
    def _check_empty(content: bytes) -> None:
        if not content:
            raise EvidenceEmptyError(message="Upload content is empty")

    def _check_size(self, content: bytes) -> None:
        if len(content) > self._max_size:
            raise EvidenceFileTooLargeError(
                message=f"File size {len(content)} exceeds limit of {self._max_size} bytes",
            )

    def _validate_image(
        self,
        *,
        content: bytes,
        declared_mime_type: str | None,
        evidence_type: EvidenceType,
        checksum: str,
    ) -> ValidatedEvidenceUpload:
        detected_format, width, height = self._decode_image(content)
        detected_mime = PIL_FORMAT_TO_MIME.get(detected_format, "")

        if not detected_mime:
            raise EvidenceMimeUnsupportedError(
                message=f"Unsupported image format: {detected_format}",
            )

        normalized_ext = PIL_FORMAT_TO_EXTENSION.get(detected_format, "")

        if declared_mime_type is not None:
            self._check_declared_mime(declared_mime_type, detected_mime)

        if width <= 0 or height <= 0:
            raise EvidenceDimensionsInvalidError(
                message=f"Non-positive image dimensions: {width}x{height}",
            )

        return ValidatedEvidenceUpload(
            evidence_type=evidence_type,
            detected_mime_type=detected_mime,
            normalized_extension=normalized_ext,
            size_bytes=len(content),
            checksum_sha256=checksum,
            width=width,
            height=height,
        )

    @staticmethod
    def _check_declared_mime(
        declared_mime_type: str,
        detected_mime: str,
    ) -> None:
        if declared_mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            raise EvidenceMimeUnsupportedError(
                message=f"Unsupported declared MIME type: {declared_mime_type}",
            )
        if declared_mime_type != detected_mime:
            raise EvidenceMimeMismatchError(
                message=(
                    f"Declared MIME {declared_mime_type} does not match detected {detected_mime}"
                ),
            )

    @staticmethod
    def _decode_image(
        content: bytes,
    ) -> tuple[str, int, int]:
        try:
            with Image.open(BytesIO(content)) as img:
                img.verify()
        except (UnidentifiedImageError, Exception) as exc:
            raise EvidenceImageInvalidError(
                message=f"Invalid image content: {exc}",
            ) from exc

        try:
            with Image.open(BytesIO(content)) as img:
                detected_format = img.format or ""
                width, height = img.size
        except Exception as exc:
            raise EvidenceImageInvalidError(
                message=f"Failed to read image metadata: {exc}",
            ) from exc

        return detected_format, width, height
