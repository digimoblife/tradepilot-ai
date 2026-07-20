"""Centralized error codes and Indonesian messages (TP-1007)."""

# Stable machine-readable error codes
AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
AUTHENTICATION_INVALID = "AUTHENTICATION_INVALID"
AUTHENTICATION_EXPIRED = "AUTHENTICATION_EXPIRED"
AUTHENTICATION_INACTIVE = "AUTHENTICATION_INACTIVE"

SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
SESSION_TRANSITION_INVALID = "SESSION_TRANSITION_INVALID"
ARCHIVE_SESSION_INVALID_STATE = "ARCHIVE_SESSION_INVALID_STATE"

EVIDENCE_FILE_UNSUPPORTED = "EVIDENCE_FILE_UNSUPPORTED"
EVIDENCE_FILE_TOO_LARGE = "EVIDENCE_FILE_TOO_LARGE"
EVIDENCE_EMPTY_FILE = "EVIDENCE_EMPTY_FILE"
EVIDENCE_IMAGE_INVALID = "EVIDENCE_IMAGE_INVALID"
EVIDENCE_DIMENSIONS_INVALID = "EVIDENCE_DIMENSIONS_INVALID"
EVIDENCE_NOT_FOUND = "EVIDENCE_NOT_FOUND"

ANALYSIS_JOB_ALREADY_ACTIVE = "ANALYSIS_JOB_ALREADY_ACTIVE"
ANALYSIS_REQUIRED_EVIDENCE_MISSING = "ANALYSIS_REQUIRED_EVIDENCE_MISSING"
ANALYSIS_TYPE_INVALID_FOR_LIFECYCLE = "ANALYSIS_TYPE_INVALID_FOR_LIFECYCLE"
ANALYSIS_JOB_NOT_RETRYABLE = "ANALYSIS_JOB_NOT_RETRYABLE"
ANALYSIS_JOB_RETRY_EXHAUSTED = "ANALYSIS_JOB_RETRY_EXHAUSTED"
ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"

ACTION_INVALID_STATE = "ACTION_INVALID_STATE"
ACTION_INVALID_INPUT = "ACTION_INVALID_INPUT"
ACTION_INVALID_RELATIONSHIP = "ACTION_INVALID_RELATIONSHIP"
ACTION_QUANTITY_INVALID = "ACTION_QUANTITY_INVALID"
ACTION_QUANTITY_MISMATCH = "ACTION_QUANTITY_MISMATCH"
ACTION_INVALID_REASON = "ACTION_INVALID_REASON"
ACTION_INVALID_TIMELINE = "ACTION_INVALID_TIMELINE"

CONTEXT_SUMMARY_NOT_FOUND = "CONTEXT_SUMMARY_NOT_FOUND"

VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"

# Indonesian user-facing messages
_ERROR_MESSAGES: dict[str, str] = {
    AUTHENTICATION_REQUIRED: "Autentikasi diperlukan. Silakan masuk terlebih dahulu.",
    AUTHENTICATION_INVALID: "Email atau kata sandi tidak valid.",
    AUTHENTICATION_EXPIRED: "Sesi telah kedaluwarsa. Silakan masuk kembali.",
    AUTHENTICATION_INACTIVE: "Akun tidak aktif. Hubungi administrator.",
    SESSION_NOT_FOUND: "Sesi perdagangan tidak ditemukan.",
    SESSION_TRANSITION_INVALID: "Status sesi saat ini tidak mengizinkan tindakan tersebut.",
    ARCHIVE_SESSION_INVALID_STATE: (
        "Sesi tidak dapat diarsipkan dalam status saat ini. "
        "Hanya sesi yang sudah selesai atau dibatalkan yang dapat diarsipkan."
    ),
    EVIDENCE_FILE_UNSUPPORTED: "Format file tidak didukung. Gunakan PNG, JPEG, atau WebP.",
    EVIDENCE_FILE_TOO_LARGE: "Ukuran berkas terlalu besar. Maksimum 10 MB.",
    EVIDENCE_EMPTY_FILE: "Berkas kosong. Silakan unggah berkas yang valid.",
    EVIDENCE_IMAGE_INVALID: "Berkas gambar tidak dapat dibaca atau rusak.",
    EVIDENCE_DIMENSIONS_INVALID: "Dimensi gambar tidak valid.",
    EVIDENCE_NOT_FOUND: "Bukti tidak ditemukan.",
    ANALYSIS_JOB_ALREADY_ACTIVE: (
        "Tugas analisis untuk tipe ini sudah aktif. "
        "Tunggu hingga tugas saat ini selesai."
    ),
    ANALYSIS_REQUIRED_EVIDENCE_MISSING: (
        "Bukti yang diperlukan belum lengkap. "
        "Silakan unggah bukti yang diperlukan terlebih dahulu."
    ),
    ANALYSIS_TYPE_INVALID_FOR_LIFECYCLE: (
        "Jenis analisis tidak sesuai dengan status sesi saat ini."
    ),
    ANALYSIS_JOB_NOT_RETRYABLE: (
        "Tugas analisis tidak dapat diulang dalam status saat ini."
    ),
    ANALYSIS_JOB_RETRY_EXHAUSTED: "Batas percobaan ulang telah habis.",
    ANALYSIS_NOT_FOUND: "Analisis tidak ditemukan.",
    ACTION_INVALID_STATE: "Status sesi tidak mengizinkan tindakan ini.",
    ACTION_INVALID_INPUT: "Nilai input tidak valid.",
    ACTION_INVALID_RELATIONSHIP: "Hubungan harga tidak valid.",
    ACTION_QUANTITY_INVALID: "Jumlah tidak valid untuk tindakan ini.",
    ACTION_QUANTITY_MISMATCH: "Jumlah tidak sesuai dengan posisi saat ini.",
    ACTION_INVALID_REASON: "Alasan penutupan tidak valid.",
    ACTION_INVALID_TIMELINE: "Waktu transaksi tidak valid.",
    CONTEXT_SUMMARY_NOT_FOUND: "Ringkasan konteks tidak ditemukan.",
    VALIDATION_ERROR: "Data yang dikirim tidak valid. Periksa kembali input Anda.",
    INTERNAL_ERROR: (
        "Terjadi kesalahan internal. Silakan coba lagi nanti."
    ),
}


def get_error_message(code: str) -> str:
    """Return the user-safe Indonesian message for an error code."""
    return _ERROR_MESSAGES.get(code, "Terjadi kesalahan.")


def status_code_for(code: str) -> int:
    """Return the appropriate HTTP status code for an error code."""
    if "AUTHENTICATION_REQUIRED" in code or code == AUTHENTICATION_INVALID:
        return 401
    if code == AUTHENTICATION_EXPIRED:
        return 401
    if code == AUTHENTICATION_INACTIVE:
        return 403
    if "NOT_FOUND" in code:
        return 404
    if "ALREADY_ACTIVE" in code:
        return 409
    if "FILE_TOO_LARGE" in code:
        return 413
    if "UNSUPPORTED" in code or "MIME_UNSUPPORTED" in code:
        return 415
    if code == VALIDATION_ERROR:
        return 422
    if code == INTERNAL_ERROR:
        return 500
    return 422
