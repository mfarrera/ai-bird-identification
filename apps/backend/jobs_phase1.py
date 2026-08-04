"""
Feina de la cua 'fase1': córrer YOLO (Model 1) sobre una detecció que
encara no l'ha passat (típicament pujada directament per un usuari, o
un vídeo de l'Edge amb confidence baixa).

Aquest mòdul NOMÉS es carrega dins del contenidor worker-phase1 (que
instal·la ultralytics/opencv, pesats) — el backend (API) no els
necessita per a res, només encua la feina per nom.
"""

import io
import os
import tempfile
import uuid

import cv2
import requests
from ultralytics import YOLO

from database import get_connection
from storage import upload_file
from queues import queue_fase2

YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", "/app/models/yolov8n.pt")
YOLO_CONF_THRESHOLD = float(os.getenv("YOLO_CONF_THRESHOLD", "0.5"))
BIRD_CLASS_NAME = os.getenv("BIRD_CLASS_NAME", "bird")

# Carreguem el model un sol cop per procés worker, no a cada feina.
_model = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(YOLO_WEIGHTS)
    return _model


def process_frame_phase1(detection_id: int):
    """
    Llegeix la detecció, baixa la imatge de MinIO, hi corre YOLO.

    - Si troba un ocell: retalla la regió, puja el retall a MinIO,
      actualitza la fila (nova url = el retall, status='fase2') i
      l'encua a la cua de fase 2.
    - Si NO en troba cap: marca la detecció com a 'done' directament
      (no hi ha res més a fer-hi, no hi havia cap ocell).
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT url FROM detections WHERE id = %s", (detection_id,))
        row = cur.fetchone()

        if row is None:
            return

        image_url = row[0]

        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        frame = cv2.imread(tmp_path)
        os.remove(tmp_path)

        if frame is None:
            cur.execute(
                "UPDATE detections SET status = 'done' WHERE id = %s",
                (detection_id,)
            )
            conn.commit()
            return

        model = _get_model()
        results = model.predict(frame, conf=YOLO_CONF_THRESHOLD, verbose=False)[0]

        best_box = None
        best_conf = 0.0

        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]

            if class_name != BIRD_CLASS_NAME:
                continue

            conf = float(box.conf[0])
            if conf > best_conf:
                best_conf = conf
                best_box = box.xyxy[0].tolist()

        if best_box is None:
            # No hi havia cap ocell: no cal fase 2.
            cur.execute(
                "UPDATE detections SET status = 'done' WHERE id = %s",
                (detection_id,)
            )
            conn.commit()
            return

        x1, y1, x2, y2 = (max(0, int(v)) for v in best_box)
        crop = frame[y1:y2, x1:x2]

        ok, buffer = cv2.imencode(".jpg", crop)
        if not ok:
            raise RuntimeError("No s'ha pogut codificar el retall")

        crop_object_name = f"crops/{uuid.uuid4().hex}.jpg"
        crop_url = upload_file(
            io.BytesIO(buffer.tobytes()),
            crop_object_name,
            content_type="image/jpeg",
        )

        cur.execute(
            "UPDATE detections SET status = 'fase2', url = %s WHERE id = %s",
            (crop_url, detection_id)
        )
        conn.commit()

        queue_fase2.enqueue("jobs_phase2.process_phase2", detection_id)

    finally:
        cur.close()
        conn.close()
