import cv2

# Definim el pipeline de GStreamer.
pipeline = (
    "udpsrc port=5000 "
    "caps=application/x-rtp,media=video,encoding-name=H264,payload=96 ! "
    "rtph264depay ! "
    "avdec_h264 ! "
    "videoconvert ! "
    "appsink"
)

# Inicialitzem la captura de vídeo passant-li el nostre pipeline.
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

# Comprovació de seguretat.
if not cap.isOpened():
    print("No s'ha pogut obrir l'stream.")
    exit()

# Configuració de la finestra de visualització.
cv2.namedWindow("YOLO Edge AI", cv2.WINDOW_NORMAL)

# Mida inicial de la finestra.
cv2.resizeWindow("YOLO Edge AI", 1280, 720)

# Bucle principal de lectura i visualització.
while True:

    ret, frame = cap.read()

    if not ret:
        continue

    cv2.imshow("YOLO Edge AI", frame)

    key = cv2.waitKey(1)

    if key == 27:      # ESC
        break

# Alliberem la connexió de xarxa/càmera i destruïm les finestres gràfiques.
cap.release()
cv2.destroyAllWindows()
