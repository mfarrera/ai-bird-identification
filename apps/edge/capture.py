import threading
import time
import cv2


class CameraCapture:
    """
    Captura frames en un thread propi (patró producer),
    per evitar que la lectura bloquegi el pipeline de processament.
    Sempre exposa el frame MÉS RECENT (no acumula cua).
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

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self):
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
