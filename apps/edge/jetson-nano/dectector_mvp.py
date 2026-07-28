import cv2
import time
from ultralytics import YOLO

# DETECTOR GENERAL
# ==========================================
# CONFIGURACIÓ
# ==========================================

MODEL_PATH = "yolo26s.engine"

PC_IP = "192.168.1.144" # Xarxa de casa
#PC_IP = "192.168.8.116" # Xarxa de la feina
PORT = 5000

WIDTH = 1280
HEIGHT = 720
FPS = 30

# ==========================================
# CARREGAR MODEL
# ==========================================

print("[INFO] Carregant model TensorRT...")

model = YOLO(MODEL_PATH, task="detect")

print("[INFO] Model carregat correctament.")

# ==========================================
# PIPELINE DE LECTURA (CSI -> OpenCV)
# ==========================================

read_pipeline = (
    "nvarguscamerasrc ! "
    f"video/x-raw(memory:NVMM),width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! "
    "nvvidconv ! "
    "video/x-raw,format=BGRx ! "
    "videoconvert ! "
    "video/x-raw,format=BGR ! "
    "appsink drop=true sync=false"
)

# ==========================================
# PIPELINE D'ESCRIPTURA (OpenCV -> RTP)
# ==========================================

write_pipeline = (
    "appsrc ! "
    f"video/x-raw,format=BGR,width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! "
    "videoconvert ! "
    "x264enc tune=zerolatency "
    "speed-preset=ultrafast "
    "bitrate=4000 ! "
    "rtph264pay config-interval=1 pt=96 ! "
    f"udpsink host={PC_IP} port={PORT} sync=false"
)

# ==========================================
# OBRIR CÀMERA
# ==========================================

print("[INFO] Obrint càmera...")

cap = cv2.VideoCapture(read_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("[ERROR] No s'ha pogut obrir la càmera.")
    exit()

# ==========================================
# OBRIR PIPELINE RTP
# ==========================================

print("[INFO] Inicialitzant transmissió RTP...")

out = cv2.VideoWriter(
    write_pipeline,
    cv2.CAP_GSTREAMER,
    0,
    FPS,
    (WIDTH, HEIGHT),
    True
)

if not out.isOpened():
    print("[ERROR] No s'ha pogut obrir el pipeline RTP.")
    cap.release()
    exit()

print("[INFO] Sistema iniciat.")
print(f"[INFO] Enviant vídeo a {PC_IP}:{PORT}")

# ==========================================
# BUCLE PRINCIPAL
# ==========================================

previous = time.time()

while True:
    # Captura d'imatge
    ret, frame = cap.read()

    if not ret:
        print("[WARNING] Frame no rebut.")
        continue

    start = time.time()
    
    # Inferència YOLO
    results = model.predict(
        frame,
        verbose=False
    )

    inference = (time.time() - start) * 1000
    
    # Dibuixa els resultats
    annotated = results[0].plot()
    
    # Calcula els FPS totals del bucle
    now = time.time()
    fps = 1 / (now - previous)
    previous = now
    
    # Imprimeix els textos per pantalla
    cv2.putText(
        annotated,
        f"FPS: {fps:.1f}",
        (20,40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0,255,0),
        2
    )

    cv2.putText(
        annotated,
        f"Inference: {inference:.1f} ms",
        (20,80),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255,255,0),
        2
    )
    
    # Enviament per xarxa
    out.write(annotated)
