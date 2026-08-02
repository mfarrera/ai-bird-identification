import cv2


class MotionDetector:
    """
    Model 1 del diagrama: 'Sensor de Moviment'.
    Fa servir substracció de fons (MOG2) per detectar si hi ha
    quelcom en moviment abans de gastar còmput en YOLO.
    """

    def __init__(self, min_area: int = 1500):
        self.min_area = min_area
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=False,
        )

    def detect(self, frame):
        """
        Retorna (hi_ha_moviment: bool, bounding_boxes: list[(x, y, w, h)])
        """
        fg_mask = self.bg_subtractor.apply(frame)

        # Neteja de soroll: erosió + dilatació
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, None, iterations=1)
        fg_mask = cv2.dilate(fg_mask, None, iterations=2)

        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        boxes = []
        for contour in contours:
            if cv2.contourArea(contour) < self.min_area:
                continue
            boxes.append(cv2.boundingRect(contour))  # (x, y, w, h)

        return len(boxes) > 0, boxes
