"""File storage — S3-compatible (AWS S3, Cloudflare R2, MinIO).

Falls back to local filesystem when S3 is not configured.
Set PIXORA_S3_BUCKET + PIXORA_S3_ACCESS_KEY + PIXORA_S3_SECRET_KEY to enable.
"""
from __future__ import annotations
import io
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

LOCAL_STORAGE_DIR = "/tmp/pixora_uploads"


async def upload_file(file_bytes: bytes, filename: str, tenant_id: str = "") -> str:
    from pixora.config.settings import settings
    key = f"{tenant_id}/{uuid.uuid4().hex[:12]}_{filename}" if tenant_id else f"{uuid.uuid4().hex[:12]}_{filename}"

    if settings.s3_bucket:
        try:
            import boto3
            kwargs: dict[str, Any] = {
                "aws_access_key_id": settings.s3_access_key,
                "aws_secret_access_key": settings.s3_secret_key,
                "region_name": settings.s3_region,
            }
            if settings.s3_endpoint:
                kwargs["endpoint_url"] = settings.s3_endpoint

            s3 = boto3.client("s3", **kwargs)
            s3.upload_fileobj(io.BytesIO(file_bytes), settings.s3_bucket, key)
            logger.info("storage: uploaded %s to s3://%s/%s", filename, settings.s3_bucket, key)
            return f"s3://{settings.s3_bucket}/{key}"
        except Exception as exc:
            logger.warning("storage: S3 upload failed: %s — using local", exc)

    os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    local_path = os.path.join(LOCAL_STORAGE_DIR, key.replace("/", "_"))
    with open(local_path, "wb") as f:
        f.write(file_bytes)
    return f"local://{local_path}"


async def download_file(storage_url: str) -> bytes:
    if storage_url.startswith("s3://"):
        from pixora.config.settings import settings
        parts = storage_url[5:].split("/", 1)
        bucket, key = parts[0], parts[1]

        import boto3
        kwargs: dict[str, Any] = {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": settings.s3_region,
        }
        if settings.s3_endpoint:
            kwargs["endpoint_url"] = settings.s3_endpoint

        s3 = boto3.client("s3", **kwargs)
        buf = io.BytesIO()
        s3.download_fileobj(bucket, key, buf)
        return buf.getvalue()

    if storage_url.startswith("local://"):
        path = storage_url[8:]
        with open(path, "rb") as f:
            return f.read()

    return b""
