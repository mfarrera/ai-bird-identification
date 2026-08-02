import os
import uuid
from datetime import datetime, timezone
import cv2


class DetectionCropper:
    """
    Retalla la regió de la detecció (amb un marge) i la guarda
    localment abans d'enviar-la al backend.
    """

    def __init__(self, output_dir: str, margin_ratio: float = 0.15):
        self.output_dir = output_dir
        self.margin_ratio = margin_ratio
        os.makedirs(self.output_dir, exist_ok=True)

    def crop(self, frame, box) -> str:
        x1, y1, x2, y2 = box
        h, w = frame.shape[:2]

        # Afegim marge perquè el retall no quedi massa ajustat a l'ocell
        box_w, box_h = x2 - x1, y2 - y1
        mx, my = int(box_w * self.margin_ratio), int(box_h * self.margin_ratio)

        x1 = max(0, x1 - mx)
        y1 = max(0, y1 - my)
        x2 = min(w, x2 + mx)
        y2 = min(h, y2 + my)

        crop = frame[y1:y2, x1:x2]

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        cv2.imwrite(filepath, crop)

        return filepath

    @staticmethod
    def timestamp_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
