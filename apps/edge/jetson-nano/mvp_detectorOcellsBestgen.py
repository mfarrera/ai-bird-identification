import cv2
import time
import logging
import requests
import os
import threading
import queue
import signal
import sys
from collections import deque
from datetime import datetime, timezone
from ultralytics import YOLO


# ----------------------
# CONFIGURACIÓ GENERAL
# ---------------------

# Model YOLO optimitzat amb TensorRT per a la Jetson Nano Orin
MODEL_PATH = "bestgen.engine"

# Adreça del servidor Cloud (Docker)
DOCKER_HOST = "192.168.1.144"

# Backend FastAPI
BACKEND_URL = f"http://{DOCKER_HOST}:8000"
DETECTION_ENDPOINT = f"{BACKEND_URL}/api/detections_frame"

# Servidor de streaming (MediaMTX)
MEDIA_SERVER = DOCKER_HOST
RTSP_PORT = 8554

# Credencials de la càmera registrades a la base de dades
CAMERA_ID = 1
PUBLISH_TOKEN = "secreto_edge_123"

# Paràmetres de captura de la càmera CSI
WIDTH = 1280
HEIGHT = 720
FPS = 30

# Emmagatzematge temporal dels retalls al dispositiu Edge
CROP_DIR = "/tmp/detection_crops"
CROP_WIDTH = None       # None = manté la resolució original del retall
CROP_HEIGHT = None      # None = manté la resolució original del retall
MAX_CROPS_AGE_HOURS = 1
CLEANUP_INTERVAL = 300  # Cada 5 minuts

# ---------------------
# FILTRES DE DETECCIÓ
#---------------------

# Només s'envien deteccions amb confiança igual o superior a aquest valor
MIN_CONFIDENCE = 0.8

# Llista d'espècies permeses. Buid significa totes.
ALLOWED_SPECIES = []

# Temps mínim entre deteccions d'una mateixa zona per evitar duplicats
MIN_DETECTION_INTERVAL = 3.0

# Cua de comunicació entre el thread d'inferència i el d'enviament
SEND_QUEUE_MAXSIZE = 200
BATCH_INTERVAL = 0.5
BATCH_MAX_SIZE = 20

os.makedirs(CROP_DIR, exist_ok=True)


# -----------------------------
# CONFIGURACIÓ DEL LOGGING
# ------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EDGE")

#------------------------------
# GESTOR DE PARADA CONTROLADA
# ------------------------------

stop_event = threading.Event()


def signal_handler(sig, frame):
    """Gestiona la parada del sistema amb Ctrl+C."""
    logger.info("Senyal de parada rebuda. Iniciant tancament controlat...")
    stop_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# -----------------------------------------
# SESSIÓ HTTP AMB CAPÇALERES D'AUTENTICACIÓ
# -----------------------------------------

http_session = requests.Session()
http_session.headers.update({
    "X-Camera-Id": str(CAMERA_ID),
    "X-Publish-Token": PUBLISH_TOKEN,
    "Connection": "keep-alive"
})


# -----------------------------------
# FUNCIÓ: EXTRACCIÓ DEL RETALL (CROP)
# ----------------------------------

def extract_crop(frame, bbox):
    """
    Extreu la subimatge corresponent a la detecció.
    Si CROP_WIDTH/CROP_HEIGHT estan definits, redimensiona;
    en cas contrari, manté la resolució original del sensor.
    """
    try:
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]

        # Acotar les coordenades als límits de la imatge
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        bird_crop = frame[y1:y2, x1:x2]

        if CROP_WIDTH and CROP_HEIGHT:
            bird_crop = cv2.resize(bird_crop, (CROP_WIDTH, CROP_HEIGHT))

        timestamp_file = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        crop_filename = f"bird_{timestamp_file}.jpg"
        crop_path = os.path.join(CROP_DIR, crop_filename)

        cv2.imwrite(crop_path, bird_crop, [cv2.IMWRITE_JPEG_QUALITY, 90])

        return crop_path, crop_filename

    except Exception as e:
        logger.error(f"Error en l'extracció del crop: {e}")
        return None, None


#----------------------------------------
# FUNCIÓ: PREPARACIÓ DE LA CÀRREGA ÚTIL
#----------------------------------------

def prepare_payload(crop_path, crop_filename, timestamp):
    """Prepara les dades per al thread d'enviament."""
    return {
        "crop_path": crop_path,
        "crop_filename": crop_filename,
        "detected_at": timestamp
    }


# ---------------------------------------------
# FUNCIÓ: ENVIAMENT DE DETECCIONS AL BACKEND
# --------------------------------------------

def send_batch(batch):
    """
    Envia un lot de deteccions al backend mitjançant peticions
    HTTP multipart/form-data (imatge + timestamp).
    """
    if not batch:
        return 0

    success_count = 0

    for item in batch:
        crop_path = item["crop_path"]
        crop_filename = item["crop_filename"]
        detected_at = item["detected_at"]

        if not os.path.exists(crop_path):
            logger.warning(f"Fitxer local no disponible: {crop_path}")
            continue

        form_data = {"detected_at": detected_at}

        try:
            with open(crop_path, 'rb') as img_file:
                files_payload = {"file": (crop_filename, img_file, "image/jpeg")}

                response = http_session.post(
                    DETECTION_ENDPOINT,
                    data=form_data,
                    files=files_payload,
                    timeout=10
                )

            if response.status_code == 200:
                success_count += 1
            else:
                logger.warning(
                    "Error del backend HTTP %d: %s",
                    response.status_code,
                    response.text[:100]
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de xarxa durant l'enviament: {e}")

    if success_count > 0:
        logger.debug("Lot enviat: %d/%d deteccions acceptades", success_count, len(batch))

    return success_count


# --------------------------------------
# FIL DE NETEJA DE FITXERS TEMPORALS
#----------------------------------------

def cleanup_worker():
    """Elimina periòdicament els crops que superen l'edat màxima."""
    logger.info("Fil de neteja de crops iniciat.")

    while not stop_event.is_set():
        try:
            now = time.time()
            max_age = MAX_CROPS_AGE_HOURS * 3600
            deleted = 0
            total_size = 0

            for filename in os.listdir(CROP_DIR):
                filepath = os.path.join(CROP_DIR, filename)
                if os.path.isfile(filepath):
                    file_age = now - os.path.getmtime(filepath)
                    file_size = os.path.getsize(filepath)

                    if file_age > max_age:
                        os.remove(filepath)
                        deleted += 1
                    else:
                        total_size += file_size

            if deleted > 0:
                logger.info(
                    "Neteja completada: %d fitxers eliminats. Espai restant: %.1f MB",
                    deleted,
                    total_size / (1024 * 1024)
                )

        except Exception as e:
            logger.error(f"Error durant la neteja de crops: {e}")

        stop_event.wait(CLEANUP_INTERVAL)

    logger.info("Fil de neteja de crops finalitzat.")


#---------------------------------
# FIL D'ENVIAMENT DE DETECCIONS
#---------------------------------

def sender_worker(send_queue):
    """
    Consumeix la cua de deteccions i les envia al backend en lots.
    S'executa en un fil independent per no bloquejar la inferència.
    """
    logger.info("Fil d'enviament de deteccions iniciat.")

    batch = []
    last_send = time.time()
    queue_saturated = False

    while not stop_event.is_set():
        try:
            payload = send_queue.get(timeout=0.2)
            batch.append(payload)

            if send_queue.qsize() < SEND_QUEUE_MAXSIZE * 0.5:
                queue_saturated = False

            current_time = time.time()
            if len(batch) >= BATCH_MAX_SIZE or (current_time - last_send >= BATCH_INTERVAL and batch):
                send_batch(batch)
                batch.clear()
                last_send = current_time

        except queue.Empty:
            current_time = time.time()
            if batch and (current_time - last_send >= BATCH_INTERVAL):
                send_batch(batch)
                batch.clear()
                last_send = current_time

        if send_queue.qsize() >= SEND_QUEUE_MAXSIZE * 0.9 and not queue_saturated:
            logger.error(
                "Cua d'enviament saturada (%d/%d). El backend no processa les dades amb prou rapidesa.",
                send_queue.qsize(),
                SEND_QUEUE_MAXSIZE
            )
            queue_saturated = True

    if batch:
        logger.info("Enviant lot final de %d deteccions.", len(batch))
        send_batch(batch)

    logger.info("Fil d'enviament de deteccions finalitzat.")


# ------------------------------------
# CÀRREGA DEL MODEL YOLO AMB TENSORRT
# ------------------------------------

logger.info("Carregant model TensorRT des de %s...", MODEL_PATH)
model = YOLO(MODEL_PATH, task="detect")
logger.info("Model carregat i llest per a la inferència.")


# ------------------------------------
# PIPELINES DE GSTREAMER
# ------------------------------------

# CSI -> OpenCV
read_pipeline = (
    "nvarguscamerasrc ! "
    f"video/x-raw(memory:NVMM),width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! "
    "nvvidconv ! "
    "video/x-raw,format=BGRx ! "
    "videoconvert ! "
    "video/x-raw,format=BGR ! "
    "appsink drop=true sync=false"
)

# OpenCV -> RTSP (MediaMTX)
write_pipeline = (
    "appsrc ! "
    f"video/x-raw,format=BGR,width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! "
    "videoconvert ! "
    "video/x-raw,format=I420 ! "
    "x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 ! "
    "h264parse ! "
    "rtspclientsink "
    f"location=rtsp://{MEDIA_SERVER}:{RTSP_PORT}/cam{CAMERA_ID} "
    f"user-id={CAMERA_ID} "
    f"user-pw={PUBLISH_TOKEN}"
)


# ------------------------------------
# INICIALITZACIÓ DE LA CÀMERA I EL STREAMING
# ------------------------------------

logger.info("Obrient connexió amb la càmera CSI...")
cap = cv2.VideoCapture(read_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    logger.error("No s'ha pogut obrir la càmera CSI. Comproveu la connexió física.")
    sys.exit(1)

logger.info("Iniciant transmissió RTSP cap a MediaMTX...")
out = cv2.VideoWriter(write_pipeline, cv2.CAP_GSTREAMER, 0, FPS, (WIDTH, HEIGHT), True)

if not out.isOpened():
    logger.warning("No s'ha pogut establir la connexió RTSP amb MediaMTX.")
    logger.warning("El sistema funcionarà sense streaming de vídeo.")
    logger.warning("Comproveu que MediaMTX estigui actiu a %s:%d", MEDIA_SERVER, RTSP_PORT)
    out = None
else:
    logger.info("Transmissió RTSP establerta correctament.")


# ------------------------------------
# LLANÇAMENT DELS FILS SECUNDARIS
# ------------------------------------
send_queue = queue.Queue(maxsize=SEND_QUEUE_MAXSIZE)

sender_thread = threading.Thread(
    target=sender_worker,
    args=(send_queue,),
    name="Sender",
    daemon=True
)

cleanup_thread = threading.Thread(
    target=cleanup_worker,
    name="Cleanup",
    daemon=True
)

sender_thread.start()
cleanup_thread.start()


# ------------------------------------
# BUCLE PRINCIPAL DE CAPTURA I INFERÈNCIA
# ------------------------------------

previous = time.time()
frame_id = 0
detections_processed = 0
detections_skipped = 0
inference_times = deque(maxlen=100)
last_detection_time = {}

crop_info = "original" if CROP_WIDTH is None else f"{CROP_WIDTH}x{CROP_HEIGHT}"

logger.info("=" * 60)
logger.info("Agent Edge per a detecció d'ocells en temps real")
logger.info("Càmera ID        : %d", CAMERA_ID)
logger.info("Resolució        : %dx%d", WIDTH, HEIGHT)
logger.info("FPS objectiu     : %d", FPS)
logger.info("Backend          : %s", BACKEND_URL)
logger.info("Servidor streaming: %s:%d", MEDIA_SERVER, RTSP_PORT)
logger.info("Confiança mínima : %.1f", MIN_CONFIDENCE)
logger.info("Espècies permeses: %s", ALLOWED_SPECIES if ALLOWED_SPECIES else "Totes")
logger.info("Cooldown per zona: %.1f s", MIN_DETECTION_INTERVAL)
logger.info("Resolució crops  : %s (JPEG 90%%)", crop_info)
logger.info("Cua màxima       : %d deteccions", SEND_QUEUE_MAXSIZE)
logger.info("Mida del lot     : %d deteccions", BATCH_MAX_SIZE)
logger.info("Streaming RTSP   : %s", "ACTIU" if out is not None else "DESACTIVAT")
logger.info("=" * 60)

try:
    while not stop_event.is_set():

        # -------- Captura del frame --------
        ret, frame = cap.read()
        if not ret:
            logger.warning("No s'ha rebut cap frame de la càmera.")
            time.sleep(0.01)
            continue

        # -------- Inferència YOLO --------
        start = time.time()
        results = model.predict(frame, verbose=False)
        inference = (time.time() - start) * 1000
        inference_times.append(inference)

        # -------- Processament de les deteccions --------
        frame_id += 1
        timestamp = datetime.now(timezone.utc).isoformat()

        for box in results[0].boxes:
            class_id = int(box.cls[0])
            species = model.names[class_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Filtrar per confiança
            if confidence < MIN_CONFIDENCE:
                detections_skipped += 1
                continue

            # Filtrar per espècie (si n'hi ha llista)
            if ALLOWED_SPECIES and species not in ALLOWED_SPECIES:
                detections_skipped += 1
                continue

            # Evitar deteccions repetides en la mateixa zona
            bbox_key = f"{x1 // 100}_{y1 // 100}"
            current_time = time.time()
            if bbox_key in last_detection_time:
                if current_time - last_detection_time[bbox_key] < MIN_DETECTION_INTERVAL:
                    detections_skipped += 1
                    continue
            last_detection_time[bbox_key] = current_time

            # Extreure i enviar el retall
            crop_path, crop_filename = extract_crop(frame, [x1, y1, x2, y2])
            if crop_path is None:
                continue

            payload = prepare_payload(crop_path, crop_filename, timestamp)

            try:
                send_queue.put_nowait(payload)
                detections_processed += 1
            except queue.Full:
                logger.error("Cua plena. Es descarta la detecció de %s.", species)
                detections_skipped += 1

        # Neteja periòdica del diccionari de duplicats
        if frame_id % 300 == 0:
            cutoff = time.time() - 10
            last_detection_time = {
                k: v for k, v in last_detection_time.items() if v > cutoff
            }

        # -------- Renderitzat del frame anotat --------
        annotated = results[0].plot()

        now = time.time()
        fps = 1 / (now - previous)
        previous = now

        avg_inference = sum(inference_times) / len(inference_times) if inference_times else 0

        cv2.putText(annotated, f"FPS: {fps:.1f}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated, f"Inferencia: {inference:.1f} ms", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.putText(annotated, f"Mitjana: {avg_inference:.1f} ms", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 100), 2)
        cv2.putText(annotated, f"Cua: {send_queue.qsize()}/{SEND_QUEUE_MAXSIZE}", (20, 160),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Informe periòdic de rendiment
        if frame_id % 150 == 0:
            logger.info(
                "Metrica: Frames=%d | FPS=%.1f | Inferencia=%.1f ms | Cua=%d | Processades=%d | Saltades=%d",
                frame_id, fps, avg_inference, send_queue.qsize(),
                detections_processed, detections_skipped
            )

        # -------- Publicació del frame al servidor de streaming --------
        if out is not None:
            out.write(annotated)

except KeyboardInterrupt:
    logger.info("Interrupció d'usuari rebuda. Iniciant tancament...")

finally:
    logger.info("Alliberant recursos del sistema...")

    stop_event.set()
    cap.release()
    if out is not None:
        out.release()
    http_session.close()

    sender_thread.join(timeout=5)
    cleanup_thread.join(timeout=5)

    logger.info(
        "Sistema aturat. Resum: %d deteccions processades, %d descartades.",
        detections_processed, detections_skipped
    )
    logger.info("Fi del programa.")
    
