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
from storage import upload_file, get_url
from queues import queue_fase2

YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", "/app/models/yolov8n.pt")
YOLO_CONF_THRESHOLD = float(os.getenv("YOLO_CONF_THRESHOLD", "0.5"))
BIRD_CLASS_NAME = os.getenv("BIRD_CLASS_NAME", "bird")

# Extensions que tractem com a vídeo (la resta es tracten com a imatge).
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# Analitzar cada frame d'un vídeo amb YOLO seria molt car en CPU. En
# comptes d'això, analitzem només 1 de cada N frames. Ajustable per
# variable d'entorn si cal afinar-ho amb proves reals.
VIDEO_FRAME_SAMPLE_STRIDE = int(os.getenv("VIDEO_FRAME_SAMPLE_STRIDE", "5"))

# Carreguem el model un sol cop per procés worker, no a cada feina.
_model = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(YOLO_WEIGHTS)
    return _model


def _find_best_bird_box(model, frame):
    """
    Corre YOLO sobre UN frame i retorna (caixa, confidence) del pardal
    amb més confidence, o (None, 0.0) si no en troba cap. Es fa servir
    tant per a imatges soles com per a cada frame mostrejat d'un vídeo.
    """
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

    return best_box, best_conf


def _extract_best_bird_frame(model, video_path):
    """
    Recorre el vídeo mostrejant 1 de cada VIDEO_FRAME_SAMPLE_STRIDE
    frames, i retorna (frame, caixa) del millor pardal trobat a tot el
    vídeo, o (None, None) si no en troba cap en cap frame mostrejat.
    """
    cap = cv2.VideoCapture(video_path)

    best_frame = None
    best_box = None
    best_conf = 0.0
    frame_index = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_index % VIDEO_FRAME_SAMPLE_STRIDE == 0:
                box, conf = _find_best_bird_box(model, frame)
                if box is not None and conf > best_conf:
                    best_conf = conf
                    best_box = box
                    best_frame = frame.copy()

            frame_index += 1
    finally:
        cap.release()

    return best_frame, best_box


def process_frame_phase1(detection_id: int):
    """
    Llegeix la detecció, baixa l'arxiu de MinIO (imatge o vídeo), hi
    corre YOLO.

    - Si troba un ocell: retalla el frame corresponent, puja el retall
      a MinIO, actualitza la fila (nova url = el retall, status='fase2')
      i l'encua a la cua de fase 2.
    - Si NO en troba cap: marca la detecció com a 'done' directament.
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT url FROM detections WHERE id = %s", (detection_id,))
        row = cur.fetchone()

        if row is None:
            return

        # A la BBDD només guardem el NOM de l'objecte a MinIO (no una URL
        # presignada ja feta): la firma d'una URL presignada va lligada a
        # l'host amb què es genera, i el backend (host network) i aquest
        # worker (xarxa bridge de Docker) hi accedeixen amb hosts diferents
        # (localhost:9000 vs minio:9000). Per això cal generar-la aquí,
        # amb el MINIO_ENDPOINT propi d'aquest worker.
        object_name = row[0]
        file_url = get_url(object_name)

        response = requests.get(file_url, timeout=30)
        response.raise_for_status()

        extension = os.path.splitext(object_name)[1].lower()
        is_video = extension in VIDEO_EXTENSIONS

        with tempfile.NamedTemporaryFile(suffix=extension or ".jpg", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        model = _get_model()

        try:
            if is_video:
                frame, best_box = _extract_best_bird_frame(model, tmp_path)
            else:
                frame = cv2.imread(tmp_path)
                best_box = None
                if frame is not None:
                    best_box, _ = _find_best_bird_box(model, frame)
        finally:
            os.remove(tmp_path)

        if frame is None or best_box is None:
            # No hi havia cap ocell (o no s'ha pogut llegir): no cal fase 2.
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
        # upload_file() retorna el mateix nom d'objecte que li passem (no
        # una URL): és el que guardem a la BBDD, perquè qui llegeixi
        # aquesta detecció més endavant (fase2, l'API, el frontend...) es
        # generi la seva pròpia URL presignada amb get_url().
        upload_file(
            io.BytesIO(buffer.tobytes()),
            crop_object_name,
            content_type="image/jpeg",
        )

        cur.execute(
            "UPDATE detections SET status = 'fase2', url = %s WHERE id = %s",
            (crop_object_name, detection_id)
        )
        conn.commit()

        queue_fase2.enqueue("jobs_phase2.process_phase2", detection_id)

    finally:
        cur.close()
        conn.close()
