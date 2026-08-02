from dataclasses import dataclass
from ultralytics import YOLO


@dataclass
class Detection:
    class_name: str
    confidence: float
    box: tuple  # (x1, y1, x2, y2) en píxels, coordenades absolutes del frame


class BirdClassifier:
    """
    Model 2 del diagrama: 'YOLO - Identificació d'Ocell'.
    Només s'executa quan MotionDetector ja ha confirmat moviment,
    per estalviar còmput (YOLO és molt més car que MOG2).
    """

    def __init__(self, weights_path: str, conf_threshold: float, target_class: str):
        self.model = YOLO(weights_path)
        self.conf_threshold = conf_threshold
        self.target_class = target_class

    def classify(self, frame) -> list[Detection]:
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            verbose=False,
        )[0]

        detections = []
        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = self.model.names[class_id]

            if class_name != self.target_class:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            confidence = float(box.conf[0])

            detections.append(
                Detection(
                    class_name=class_name,
                    confidence=confidence,
                    box=(x1, y1, x2, y2),
                )
            )

        return detections
