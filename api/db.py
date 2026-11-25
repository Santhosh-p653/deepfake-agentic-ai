
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from .models import Base, ProcessingStatus
from .logger import get_logger

logger = get_logger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    else:
        engine = None
        SessionLocal = None
except Exception:
    engine = None
    SessionLocal = None


def init_db():
    if not engine:
        raise OperationalError(
            "DATABASE_URL not set or engine is uninitialized", params=None, orig=None
        )
    try:
        Base.metadata.create_all(bind=engine)
        logger.info('{"message": "Database initialised, tables ready"}')
    except Exception:
        logger.exception('{"message": "Database init failed"}')
        raise


def get_db():
    if not SessionLocal:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection():
    if not engine:
        return False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True
    except Exception:
        logger.warning('{"message": "Database connection check failed"}')
        return False


def count_active_temp_files(db) -> int:
    """
    Count files currently in temp_stored or processing state.
    Locks active rows to prevent race conditions during cap enforcement.
    Avoids FOR UPDATE in subqueries or with aggregate functions (unsupported in PostgreSQL).
    """
    from .models import MediaUpload, ProcessingStatus

    rows = (
        db.query(MediaUpload.id)
        .filter(
            MediaUpload.status.in_([ProcessingStatus.temp_stored, ProcessingStatus.processing])
        )
        .with_for_update()
        .all()
    )
    return len(rows)


def update_status(
    db,
    record_id: int,
    new_status: ProcessingStatus,
    temp_path: str = None,
    processed_at=None,
):
    """Single-place status transition. Always call this instead of mutating inline."""
    from .models import MediaUpload

    record = (
        db.query(MediaUpload)
        .filter(MediaUpload.id == record_id)
        .with_for_update()
        .first()
    )
    if not record:
        logger.warning(
            '{"message": "Status update skipped, record not found", "id": %d}',
            record_id,
        )
        return
    status_enum = (
        new_status
        if isinstance(new_status, ProcessingStatus)
        else ProcessingStatus(new_status)
    )
    record.status = status_enum
    if temp_path is not None:
        record.temp_path = temp_path
    if processed_at is not None:
        record.processed_at = processed_at
    db.commit()
    logger.info(
        '{"message": "Status updated", "id": %d, "status": "%s"}',
        record_id,
        status_enum.value,
    )
