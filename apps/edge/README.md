# Capa Edge — simulador (Docker)

⚠️ Aquest mòdul és un **simulador genèric** per fer demos/proves locals
**sense maquinari Jetson real** (OpenCV + ffmpeg, corre a qualsevol PC/Docker).
Per als scripts que corren realment sobre el Jetson Nano (GStreamer + TensorRT
+ càmera CSI), veure `jetson-nano/` en aquest mateix directori.

Worker Python que implementa el pipeline del diagrama d'arquitectura:

```
Càmera → Captura (OpenCV) → Model 1: Moviment (MOG2)
    → Model 2: YOLO (identificació d'ocell) → Cropping → Enviament API
    → Stream processat (baixa resolució) → apps/mediaserver (RTSP push)
```

Nota: al Jetson real (`jetson-nano/`), el "Model 1" no és substracció de
fons sinó un primer pas YOLO genèric (`yolo26s.engine`) — aquest simulador
fa servir MOG2 perquè és molt més lleuger i no necessita cap `.engine`
compilat, útil només per validar el flux de dades de cap a cap.

## Instal·lació

```bash
cd apps/edge
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Cal `ffmpeg` instal·lat al sistema (`apt install ffmpeg`).

## Configuració (.env)

```env
BACKEND_URL=http://127.0.0.1:8000
CAMERA_ID=1
PUBLISH_TOKEN=<publish_token de la taula camera>
CAMERA_SOURCE=rtsp://usuari:pass@192.168.1.50/stream1
MEDIASERVER_RTSP_URL=rtsp://127.0.0.1:8554
YOLO_WEIGHTS=models/bird_yolov8n.pt
```

## Execució

```bash
python main.py
```

## Docker

Construir la imatge:

```bash
cd apps/edge
docker build -t edge-worker .
```

Executar-la, muntant els pesos YOLO i les carpetes de sortida com a volums,
i passant la configuració via `.env`:

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/crops:/app/crops \
  --network host \
  edge-worker
```

Notes sobre el `docker run`:

- `--network host`: simplifica l'accés a la càmera RTSP de la xarxa local
  del centre i a `BACKEND_URL`/`MEDIASERVER_RTSP_URL` si corren en altres
  contenidors del mateix host. Si prefereixes xarxa aïllada, defineix una
  xarxa Docker compartida amb backend i MediaMTX enlloc de `host`.
- Si la font és una **webcam USB** (`CAMERA_SOURCE=0`) en lloc d'un stream
  RTSP, cal exposar el dispositiu amb `--device /dev/video0:/dev/video0`.
- Els volums de `models/` i `crops/` eviten haver de reconstruir la imatge
  cada cop que canvies els pesos YOLO, i persisteixen els retalls entre
  reinicis del contenidor.

## ⚠️ Peça pendent al backend

El backend actual (`DetectionCreate`) espera un camp `url` de tipus string,
però no hi ha cap endpoint per pujar l'arxiu binari de la imatge retallada.
Cal afegir-ne un a `apps/backend/main.py`, per exemple:

```python
import shutil
from fastapi import UploadFile, File
from fastapi.staticfiles import StaticFiles

UPLOAD_DIR = "uploads/detections"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serveix els fitxers pujats com a estàtics
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.post("/api/detections/upload-image")
def upload_detection_image(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"url": f"/uploads/detections/{filename}"}
```

Això és una solució temporal amb disc local. Quan s'implementi la capa de
Persistència amb **MinIO** (segons el diagrama), aquest endpoint hauria de
pujar l'objecte a MinIO en lloc de disc local i retornar la URL del bucket.

## Seguretat

`POST /api/detections/upload-image` requereix les capçaleres
`X-Camera-Id` i `X-Publish-Token`, validades contra la columna
`publish_token` de la taula `camera` (mateix mecanisme que
`/api/mediamtx/auth`). Sense aquestes capçaleres, o amb un token
incorrecte, el backend respon `401`. `BackendClient` ja les afegeix
automàticament a partir de `config.PUBLISH_TOKEN`.

## Notes de disseny

- **Cooldown entre deteccions**: evita saturar el backend enviant la mateixa
  detecció repetidament frame rere frame (5s configurable a `main.py`).
- **Model 1 abans que Model 2**: YOLO només s'executa si MOG2 ja ha detectat
  moviment, estalviant còmput a l'Edge (important si va sobre Raspberry Pi
  o maquinari limitat).
- **Autenticació de publicació**: la URL RTSP cap a MediaMTX inclou
  `user={camera_id}&pass={publish_token}`, que MediaMTX reenvia a
  `POST /api/mediamtx/auth` del backend per validar-los (ja implementat).
- **Reconnexió de càmera**: `CameraCapture` reintenta la connexió si la
  lectura RTSP falla, útil per xarxes de centre inestables.
- **Pendent**: gestió de reconnexió del subprocés ffmpeg si mor
  (`StreamPublisher`), rotació/neteja de crops locals, i logging estructurat
  en lloc de `print`.
