import os
from datetime import timedelta

from minio import Minio

# El backend corre amb network_mode: host, així que arriba a MinIO pel
# port publicat a l'host (localhost:9000). Futurs workers, si corren dins
# de la xarxa normal de Docker, hi arribaran per MINIO_ENDPOINT=minio:9000.
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "detections")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)


def _ensure_bucket():
    if not _client.bucket_exists(MINIO_BUCKET):
        _client.make_bucket(MINIO_BUCKET)


def upload_file(file_obj, object_name: str, content_type: str = "application/octet-stream") -> str:
    """
    Puja un fitxer (imatge o vídeo) al bucket de MinIO i retorna una URL
    temporal per llegir-lo (com els tokens de stream/publicació que ja
    fa servir el projecte, no un bucket públic).
    """

    _ensure_bucket()

    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)

    _client.put_object(
        MINIO_BUCKET,
        object_name,
        file_obj,
        length=size,
        content_type=content_type,
    )

    return get_url(object_name)


def get_url(object_name: str, expires_minutes: int = 60) -> str:
    return _client.presigned_get_object(
        MINIO_BUCKET,
        object_name,
        expires=timedelta(minutes=expires_minutes),
    )
