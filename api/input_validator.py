import magic
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpeg", ".jpg", ".png", ".mp4"}
ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpeg", ".jpg"],
    "image/png": [".png"],
    "video/mp4": [".mp4"],
}

def validate_input(filename: str, file_bytes: bytes) -> tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Rejected: '{ext}' is not an accepted format. Use .jpeg, .png, or .mp4."

    mime = magic.from_buffer(file_bytes[:2048], mime=True)
    allowed_exts_for_mime = ALLOWED_MIME_TYPES.get(mime)
    if allowed_exts_for_mime is None:
        return False, f"Rejected: file encoding does not match any accepted type (detected: {mime})."
    if ext not in allowed_exts_for_mime:
        return False, f"Rejected: extension '{ext}' does not match detected encoding '{mime}'."

    return True, "ok"
