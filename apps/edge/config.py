import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Backend (Cloud) ---
    BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    CAMERA_ID = int(os.getenv("CAMERA_ID", "1"))
    PUBLISH_TOKEN = os.getenv("PUBLISH_TOKEN")  # coincideix amb camera.publish_token a la BBDD

    # --- Font de vídeo local (càmera física connectada a l'Edge) ---
    # Pot ser un index (0, 1...) per a una webcam USB, o una URL RTSP/HTTP
    SOURCE = os.getenv("CAMERA_SOURCE", "0")

    # --- Media Server (destí del stream processat) ---
    MEDIASERVER_RTSP_URL = os.getenv(
        "MEDIASERVER_RTSP_URL", "rtsp://127.0.0.1:8554"
    )

    @property
    def mediaserver_publish_url(self) -> str:
        # El Media Server (MediaMTX) autentica via /api/mediamtx/auth amb
        # user=camera_id, password=publish_token. Les credencials RTSP van
        # al userinfo de la URL (rtsp://user:pass@host:port/path), NO com a
        # query params, que és el que fa servir ffmpeg per publicar-les.
        scheme_sep = "://"
        protocol, rest = self.MEDIASERVER_RTSP_URL.split(scheme_sep, 1)
        return f"{protocol}{scheme_sep}{self.CAMERA_ID}:{self.PUBLISH_TOKEN}@{rest}/cam{self.CAMERA_ID}"

    # --- Detecció de moviment (Model 1) ---
    MOTION_MIN_AREA = int(os.getenv("MOTION_MIN_AREA", "1500"))  # px^2, filtra soroll

    # --- YOLO (Model 2) ---
    YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", "models/bird_yolov8n.pt")
    YOLO_CONF_THRESHOLD = float(os.getenv("YOLO_CONF_THRESHOLD", "0.5"))
    BIRD_CLASS_NAME = os.getenv("BIRD_CLASS_NAME", "bird")

    # --- Emmagatzematge local temporal de crops ---
    CROPS_DIR = os.getenv("CROPS_DIR", "./crops")

    # --- Resolució del stream processat (baixa resolució per estalviar ample de banda) ---
    STREAM_WIDTH = int(os.getenv("STREAM_WIDTH", "640"))
    STREAM_HEIGHT = int(os.getenv("STREAM_HEIGHT", "360"))


config = Config()
