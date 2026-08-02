import subprocess


class StreamPublisher:
    """
    Publica els frames processats (amb les deteccions dibuixades, opcional)
    cap a MediaMTX via RTSP push, fent servir ffmpeg com a subprocés.

    MediaMTX autentica aquesta publicació contra
    POST /api/mediamtx/auth (action=publish) del backend, comprovant
    camera_id + publish_token — per això la URL inclou user/pass.
    """

    def __init__(self, rtsp_url: str, width: int, height: int, fps: int = 15):
        self.rtsp_url = rtsp_url
        self.width = width
        self.height = height
        self.fps = fps
        self.process = None

    def start(self):
        command = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.width}x{self.height}",
            "-r", str(self.fps),
            "-i", "-",  # llegeix frames per stdin
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-f", "rtsp",
            self.rtsp_url,
        ]

        self.process = subprocess.Popen(command, stdin=subprocess.PIPE)
        return self

    def push_frame(self, frame):
        if self.process is None or self.process.stdin is None:
            return
        try:
            self.process.stdin.write(frame.tobytes())
        except BrokenPipeError:
            # El procés ffmpeg ha mort; caldria reiniciar-lo (no gestionat aquí)
            pass

    def stop(self):
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()
            self.process.terminate()
