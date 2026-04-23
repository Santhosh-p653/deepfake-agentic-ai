
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base, ProcessingStatus

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    engine = create_engine(DATABASE_URL) if DATABASE_URL else None
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception:
    engine = None
    SessionLocal = None


def init_db():
    if engine:
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass


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
    except SQLAlchemyError:
        return False


def count_active_temp_files(db) -> int:
    """
    Count files currently in temp_stored or processing state.
    Subquery locks rows first, then counts — avoids FOR UPDATE with aggregate error.
    """
    result = db.execute(
        text("""
            SELECT COUNT(*) FROM (
                SELECT id FROM media_uploads
                WHERE status IN ('temp_stored', 'processing')
                FOR UPDATE
            ) AS locked_rows
        """)
    )
    return result.scalar()


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
        return
    record.status = new_status
    if temp_path is not None:
        record.temp_path = temp_path
    if processed_at is not None:
        record.processed_at = processed_at
    db.commit()
