# --- Base amb dependències de sistema per a OpenCV i ffmpeg ---
FROM python:3.11-slim

# Dependències de sistema:
# - ffmpeg: publicació RTSP cap a MediaMTX
# - libgl1, libglib2.0-0: requerides per opencv-python en entorns headless
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Els pesos YOLO no es copien a la imatge (poden ser pesats i canviar
# sovint): es munten com a volum en temps d'execució.
VOLUME ["/app/models", "/app/crops"]

# Sense usuari root en producció
RUN useradd --create-home edge
USER edge

CMD ["python", "main.py"]
