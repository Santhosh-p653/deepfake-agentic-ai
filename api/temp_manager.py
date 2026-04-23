import os
import uuid
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEMP_DIR = Path("/app/tmp")
TEMP_FILE_CAP = 2


def ensure_temp_dir():
    """Create /app/tmp at startup with correct permissions if it doesn't exist."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(TEMP_DIR, 0o700)
    logger.info("Temp dir ready: path=%s", TEMP_DIR)


def write_to_temp(file_bytes: bytes, original_filename: str) -> str:
    """
    Write file bytes to /app/tmp with a UUID-prefixed filename.
    Returns the full path as a string.
    """
    ext = original_filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    dest = TEMP_DIR / unique_name
    with open(dest, "wb") as f:
        f.write(file_bytes)
    logger.info("Write temp file: path=%s size_bytes=%d", dest, len(file_bytes))
    return str(dest)


def delete_from_temp(temp_path: str):
    """
    Delete a file from /app/tmp. Safe to call even if file no longer exists.
    """
    path = Path(temp_path)
    if path.exists():
        path.unlink()
        logger.info("Delete temp file: path=%s", temp_path)
    else:
        logger.warning("Temp file already absent on delete: path=%s", temp_path)


def cleanup_on_startup(db):
    """
    Startup recovery routine:
    1. Delete any file in /app/tmp not referenced by an active DB row.
    2. Reset any stuck 'processing' rows to 'failed' and delete their temp files.
    3. Delete any orphaned files on disk with no DB row at all.
    """
    from .models import MediaUpload, ProcessingStatus
    from .db import update_status
    from datetime import datetime

    if not db:
        logger.warning("Startup cleanup skipped: no DB session")
        return

    # Reset stuck processing rows
    stuck = db.query(MediaUpload).filter(
        MediaUpload.status == ProcessingStatus.processing
    ).all()
    for row in stuck:
        if row.temp_path:
            delete_from_temp(row.temp_path)
        update_status(db, row.id, ProcessingStatus.failed, processed_at=datetime.utcnow())
        logger.info("Startup reset stuck row: id=%d filename=%s", row.id, row.filename)

    # Collect all temp_paths the DB knows about
    active_paths = set()
    active_rows = db.query(MediaUpload).filter(
        MediaUpload.status == ProcessingStatus.temp_stored
    ).all()
    for row in active_rows:
        if row.temp_path:
            active_paths.add(row.temp_path)

    # Delete any file on disk not in active_paths
    if TEMP_DIR.exists():
        for f in TEMP_DIR.iterdir():
            if str(f) not in active_paths:
                f.unlink()
                logger.info("Startup deleted orphan file: path=%s", f)
