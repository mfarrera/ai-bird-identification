import threading
import time
import cv2


class CameraCapture:
    """
    Captura frames en un thread propi (patró producer),
    per evitar que la lectura bloquegi el pipeline de processament.
    Sempre exposa el frame MÉS RECENT (no acumula cua).

    Si la font és un fitxer local de vídeo (te un FRAME_COUNT conegut),
    es llegeix sencer a memoria un sol cop a l'arrencada i es fa un
    bucle per index (frames[i % total]) -- evita dependre del seek
    d'OpenCV (CAP_PROP_POS_FRAMES), que per alguns codecs/contenidors
    no es tan instantani com hauria i deixava un buit real al stream
    publicat cada vegada que el video arribava al final (causa del
    bufferStalledError a hls.js).
    """

    def __init__(self, source: str):
        # source pot ser un int (webcam) o una URL RTSP/HTTP
        try:
            source = int(source)
        except ValueError:
            pass

        self.source = source
        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"No s'ha pogut obrir la font de vídeo (CAMERA_SOURCE={source!r}).\n"
                f"  - Si és un número (p. ex. 0), és una webcam: cal exposar-la al "
                f"contenidor amb 'devices: [\"/dev/video0:/dev/video0\"]' al docker-compose.yml "
                f"(només funciona a Linux; a macOS/Windows corre l'edge fora de Docker).\n"
                f"  - Si és una ruta de fitxer (p. ex. /app/media/sample.mp4), comprova que "
                f"el fitxer existeix dins del contenidor: 'docker compose exec edge ls /app/media'.\n"
                f"  - Si és una URL RTSP, comprova connectivitat de xarxa des del contenidor."
            )

        self._lock = threading.Lock()
        self._frame = None
        self._running = False
        self._thread = None

        self._cached_frames = None

        frame_count = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if frame_count > 0:
            print(f"[capture] Fitxer local detectat, carregant {int(frame_count)} frames a memoria...")
            frames = []
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break
                frames.append(frame)

            self.cap.release()
            self._cached_frames = frames
            print(f"[capture] {len(frames)} frames carregats. Bucle per index (sense seek).")

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self):
        if self._cached_frames is not None:
            self._update_from_cache()
        else:
            self._update_from_live_source()

    def _update_from_cache(self):
        # No intentem simular el fps real del fitxer aqui -- el ritme
        # de publicacio el marca el bucle principal (main.py) amb el
        # seu propi time.sleep basat en STREAM_FPS. Aqui nomes cal
        # mantenir sempre disponible el frame "actual", el mes fresc
        # possible, sense fer-ho tan rapid que gasti CPU de franc.
        total = len(self._cached_frames)

        if total == 0:
            return

        i = 0
        while self._running:
            with self._lock:
                self._frame = self._cached_frames[i % total].copy()

            i += 1
            time.sleep(0.01)

    def _update_from_live_source(self):
        while self._running:
            ok, frame = self.cap.read()

            if not ok:
                # Reintent de connexió (útil per RTSP inestable)
                time.sleep(1)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.source)
                continue

            with self._lock:
                self._frame = frame

    def read(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self.cap.release()
