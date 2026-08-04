import requests


class BackendClient:
    """
    Encapsula la comunicació amb el backend Cloud.

    L'autenticació es fa amb el mateix publish_token que la càmera ja
    fa servir per publicar el stream a MediaMTX (/api/mediamtx/auth),
    enviat via les capçaleres X-Camera-Id / X-Publish-Token.
    """

    def __init__(self, base_url: str, camera_id: int, publish_token: str):
        self.base_url = base_url.rstrip("/")
        self.camera_id = camera_id
        self.publish_token = publish_token

    def _auth_headers(self) -> dict:
        return {
            "X-Camera-Id": str(self.camera_id),
            "X-Publish-Token": self.publish_token,
        }

    def send_frame_detection(self, image_path: str, detected_at: str) -> dict:
        """
        Una sola crida multipart a /api/detections_frame: la imatge i
        les dades de la detecció van juntes. El backend s'encarrega de
        pujar-la a MinIO i crear la fila a la BBDD.
        """

        with open(image_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/api/detections_frame",
                headers=self._auth_headers(),
                files={"file": f},
                data={"detected_at": detected_at},
                timeout=10,
            )
        response.raise_for_status()
        return response.json()

    def send_video_detection(
        self,
        video_path: str,
        detected_at: str,
        duration: int | None = None,
        confidence: float | None = None,
    ) -> dict:
        """
        Anàleg a send_frame_detection però per a vídeo. 'confidence' és
        opcional: si l'Edge ja ha corregut YOLO sobre el vídeo i està
        prou segur, el backend es pot estalviar repetir la fase 1.
        """

        data = {"detected_at": detected_at}
        if duration is not None:
            data["duration"] = duration
        if confidence is not None:
            data["confidence"] = confidence

        with open(video_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/api/detections_video",
                headers=self._auth_headers(),
                files={"file": f},
                data=data,
                timeout=30,
            )
        response.raise_for_status()
        return response.json()
