
import os
import io
from datetime import timedelta
from minio import Minio
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
from minio.commonconfig import Filter
from .logger import get_logger

logger = get_logger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepfakemedia")


def get_minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def ensure_bucket():
    """Create bucket if it doesn't exist, then apply 30-day expiry lifecycle rule."""
    client = get_minio_client()
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        logger.info('{"message": "MinIO bucket created", "bucket": "%s"}', MINIO_BUCKET)
    else:
        logger.info('{"message": "MinIO bucket exists", "bucket": "%s"}', MINIO_BUCKET)

    config = LifecycleConfig(
        [
            Rule(
                status="Enabled",
                rule_filter=Filter(prefix=""),
                rule_id="auto-delete-30-days",
                expiration=Expiration(days=30),
            )
        ]
    )
    client.set_bucket_lifecycle(MINIO_BUCKET, config)
    logger.info(
        '{"message": "MinIO lifecycle rule set", "bucket": "%s", "expiry_days": 30}',
        MINIO_BUCKET,
    )


def upload_to_minio(temp_path: str, object_name: str) -> str:
    """
    Upload file from temp_path to MinIO.
    Returns the object name (stored as drive_path in DB).
    """
    client = get_minio_client()
    with open(temp_path, "rb") as f:
        file_bytes = f.read()
    file_size = len(file_bytes)
    client.put_object(
        MINIO_BUCKET,
        object_name,
        io.BytesIO(file_bytes),
        length=file_size,
    )
    logger.info(
        '{"message": "Upload to MinIO complete", "object": "%s", "size_bytes": %d}',
        object_name,
        file_size,
    )
    return object_name


def get_minio_url(object_name: str, expires_hours: int = 24) -> str:
    """
    Generate a presigned URL for re-accessing a file from MinIO.
    Default expiry: 24 hours.
    """
    client = get_minio_client()
    url = client.presigned_get_object(
        MINIO_BUCKET,
        object_name,
        expires=timedelta(hours=expires_hours),
    )
    logger.info(
        '{"message": "Presigned URL generated", "object": "%s", "expires_hours": %d}',
        object_name,
        expires_hours,
    )
    return url
