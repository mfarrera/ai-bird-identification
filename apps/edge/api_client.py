import requests


class BackendClient:
    """
    Encapsula la comunicació amb el backend Cloud.

    L'autenticació dels endpoints de deteccions es fa amb el mateix
    publish_token que la càmera ja fa servir per publicar el stream a
    MediaMTX (/api/mediamtx/auth), enviat via les capçaleres
    X-Camera-Id / X-Publish-Token.
    """

    def __init__(self, base_url: str, camera_id: int, publish_token: str, detection_type_id: int = 1):
        self.base_url = base_url.rstrip("/")
        self.camera_id = camera_id
        self.publish_token = publish_token
        self.detection_type_id = detection_type_id

    def _auth_headers(self) -> dict:
        return {
            "X-Camera-Id": str(self.camera_id),
            "X-Publish-Token": self.publish_token,
        }

    def upload_image(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{self.base_url}/api/detections/upload-image",
                files={"file": f},
                headers=self._auth_headers(),
                timeout=10,
            )
        response.raise_for_status()
        return response.json()["url"]

    def send_frame_detection(self, image_path: str, detected_at: str) -> dict:
        image_url = self.upload_image(image_path)

        payload = {
            "id_camera": self.camera_id,
            "detected_at": detected_at,
            "type": self.detection_type_id,
            "status": "waiting",
            "url": image_url,
        }

        response = requests.post(
            f"{self.base_url}/api/detections/frame",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
