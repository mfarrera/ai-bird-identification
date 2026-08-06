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
    Puja un fitxer (imatge o vídeo) al bucket de MinIO i retorna el NOM
    DE L'OBJECTE (no una URL).

    Abans retornava directament una URL presignada, però la signatura
    d'una URL presignada va lligada a l'host amb què es genera
    (X-Amz-SignedHeaders=host) — una URL generada pel backend amb
    MINIO_ENDPOINT=localhost:9000 no és vàlida per a un worker que hi
    accedeix per minio:9000, encara que la connexió TCP fos possible.
    A més, una URL presignada caduca als 60 minuts, així que guardar-la
    "cuinada" a la BBDD tampoc serviria si la detecció triga a
    processar-se.

    Per això cada component ha de cridar get_url(object_name) pel seu
    compte, en el moment que la necessiti, amb el seu propi
    MINIO_ENDPOINT — no reutilitzar una URL generada per un altre procés.
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

    return object_name


def get_url(object_name: str, expires_minutes: int = 60) -> str:
    return _client.presigned_get_object(
        MINIO_BUCKET,
        object_name,
        expires=timedelta(minutes=expires_minutes),
    )
