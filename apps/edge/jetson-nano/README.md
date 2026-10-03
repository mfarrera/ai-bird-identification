# Mòdul Edge: Jetson Nano Orin - Detecció i Streaming en Temps Real


Aquest mòdul implementa el component *Edge Computing* del sistema distribuït de monitoratge i detecció d'avifauna en temps real. S'executa sobre una plataforma encastada **NVIDIA Jetson Orin Nano** amb un sensor de visió CSI (Sony IMX219).

La seva responsabilitat comprèn l'adquisició de vídeo accelerada per maquinari, la inferència neuronal mitjançant motors TensorRT serialitzats, la retransmissió de vídeo anotat per RTSP i la tramesa asíncrona de retalls visuals (*crops*) i metadades cap al servidor Cloud.

## 1. Arquitectura del Flux de Dades

El mòdul utilitza un patró concurrent productor-consumidor per desacoblar el cicle de captura i inferència respecte a les operacions d'E/S i la latència de xarxa:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NVIDIA Jetson Orin Nano                         │
│                                                                         │
│   ┌──────────────┐                                                      │
│   │  Càmera CSI  │                                                      │
│   │   (IMX219)   │                                                      │
│   └──────┬───────┘                                                      │
│          │ GStreamer: nvarguscamerasrc (Memòria unificada NVMM)         │
│          ▼                                                             │
│   ┌──────────────┐     Inferència                                       │
│   │ edge_jetson  │──── TensorRT ───▶ Bounding Boxes i Classificació     │
│   │   (OpenCV)   │                                                      │
│   └──────┬───────┴──────────────┬────────────────────────┐              │
│          │                      │                        │              │
│          │ VideoWriter          │ Retall (JPEG 90%)      │ Mètriques    │
│          ▼                                ▼                                   ▼              │
│   ┌──────────────┐       ┌──────────────┐          ┌───────────┐        │
│   │ Emissió RTSP │       │ Cua de Lots  │          │    Fil    │        │
│   │(key-int=30)  │       │ (Thread-Safe)│          │  Neteja   │        │
│   └──────┬───────┘       └──────┬───────┘          └─────┬─────┘        │
│          │                      │                        │              │
└──────────┼──────────────────────┼────────────────────────┼──────────────┘
           │ RTSP (:8554)         │ HTTP Multipart (:8000) │ FS Local (/tmp)
                ▼                                ▼                                    ▼
    ┌──────────────┐       ┌──────────────┐         ┌──────────────┐
    │   MediaMTX   │       │   Backend    │         │  Purgat de   │
    │ (Streaming)  │       │  (FastAPI)   │         │Crops (> 1 h) │
    └──────┬───────┘       └──────┬───────┘         └──────────────┘
           │ HLS                  │ S3 API
                ▼                                ▼
     Visualització          Base de Dades
       Frontend             (SeaweedFS / PG)

```

## 2. Estructura del Mòdul

```
edge/
├── config/
│   ├── entorn.env               # Fitxer de configuració actiu (no versionat)
│   └── entorn.env.example       # Plantilla de configuració base
├── dades/                       # Emmagatzematge temporal local (retalls i dades de treball)
├── docs/                        # Documentació tècnica i diagrames del mòdul
├── models/
│   ├── bestgen.pt               # Pesos originals de PyTorch
│   └── bestgen.engine           # Motor compilat de TensorRT (FP16)
├── scripts/                     # Scripts auxiliars de desplegament i manteniment
├── build.log                    # Registre de compilació de la imatge Docker
├── docker-compose.yml           # Orquestració del servei i perifèrics (NVIDIA runtime)
├── Dockerfile                   # Imatge basada en dustynv/l4t-pytorch
├── edge_jetson.py               # Codi font principal de l'agent Edge
├── README.md                    # Documentació tècnica del mòdul

```

## 3. Configuració (`config/entorn.env`)

Tots els paràmetres operatius es desacoblen del codi mitjançant variables d'entorn:

```
# --- Xarxa i Serveis Cloud ---
DOCKER_HOST=192.168.1.144
BACKEND_URL=http://192.168.1.144:8000
MEDIA_SERVER=192.168.1.144
RTSP_PORT=8554

# --- Identificació i Seguretat ---
CAMERA_ID=1
PUBLISH_TOKEN=secreto_edge_123

# --- Model ---
MODEL_PATH=/app/models/bestgen.engine

# --- Captura CSI ---
WIDTH=1920
HEIGHT=1080
FPS=30

# --- Filtres de Decisió ---
MIN_CONFIDENCE=0.8
MIN_DETECTION_INTERVAL=3.0
ALLOWED_SPECIES=

# --- Gestió Local d'Evidències (Crops) ---
CROP_DIR=/tmp/detection_crops
MAX_CROPS_AGE_HOURS=1
CLEANUP_INTERVAL=300

# --- Concurrència d'Enviament ---
SEND_QUEUE_MAXSIZE=200
BATCH_INTERVAL=0.5
BATCH_MAX_SIZE=20

```

## 4. Desplegament i Execució

### 4.1. Requisits Prèvis al Host (Jetson)

* **NVIDIA JetPack:** 6.x (L4T r36.x o superior).
* **Docker & Runtime:** `nvidia-container-toolkit` configurat amb el runtime predeterminat per a Docker.

```
# Configuració del runtime NVIDIA al dimoni de Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

```

### 4.2. Posada en Marxa

1. Creació del fitxer de configuració local:

   ```
   cp config/entorn.env.example config/entorn.env
   nano config/entorn.env
   
   ```

2. Construcció i arrencada del contenidor:

   ```
   docker compose build
   docker compose up -d
   
   ```

3. Comprovació dels logs:

   ```
   docker compose logs -f edge
   
   ```

## 5. Característiques Clau

* **Zero-Copy Memory:** Ingesta directa de la càmera CSI a la GPU via NVMM, minimitzant l'ús de CPU.
* **Optimitzat per a HLS:** Control de GOP (`key-int-max=30`) per garantir un streaming web estable sense talls de segments.
* **Qualitat Asimètrica:** Streaming en viu optimitzat (500 kbps, baixa latència) vs. evidències (*crops*) en alta qualitat (JPEG 90%).
* **Tolerància a Fallades:** Enviament asíncron en lots amb cues thread-safe. Si la xarxa cau, la inferència no es bloqueja.

## 6. Verificació i Diagnòstic

* **Comprovació de connectivitat amb el servidor RTSP:**

  ```
  nc -zv 192.168.1.144 8554
  
  ```

* **Visualització del flux en directe (RTSP):**

  ```
  vlc rtsp://192.168.1.144:8554/cam1
  
  ```

* **Visualització del flux HLS (navegador web):**

  ```text
  http://192.168.1.144:8888/cam1/
  ```

* **Inspecció dels crops pujats al magatzem d'objectes (SeaweedFS Filer):**

  ```
  http://192.168.1.144:9001/buckets/detections/detections/1/
  
  ```
