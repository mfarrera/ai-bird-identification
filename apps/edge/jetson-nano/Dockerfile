# Imatge base amb PyTorch + OpenCV (GStreamer) per a Jetson
FROM dustynv/l4t-pytorch:r36.4.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Plugins GStreamer (incloent RTSP)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        gstreamer1.0-rtsp \
        libgstrtspserver-1.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Forcem l'índex PyPI oficial (el mirror jetson.webredirect.org no té ultralytics)
ENV PIP_INDEX_URL=https://pypi.org/simple \
    PIP_TRUSTED_HOST=pypi.org

# ultralytics SENSE dependències: no volem que pip sobrescrigui
# el torch-CUDA ni l'OpenCV-GStreamer que ja porta la imatge base
RUN pip3 install --no-cache-dir --no-deps ultralytics \
    && pip3 install --no-cache-dir \
         requests numpy pillow pyyaml tqdm psutil py-cpuinfo \
         matplotlib pandas scipy \
    && python3 -c "from ultralytics import YOLO; print('ultralytics OK')"

COPY edge_jetson.py /app/app.py

CMD ["python3", "/app/app.py"]
