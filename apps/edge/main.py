import time
import cv2

from config import config
from capture import CameraCapture
from motion_detector import MotionDetector
from bird_classifier import BirdClassifier
from cropper import DetectionCropper
from api_client import BackendClient
from stream_publisher import StreamPublisher


# Cooldown mínim entre deteccions enviades (evita saturar el backend
# amb la mateixa detecció repetida frame rere frame)
DETECTION_COOLDOWN_SECONDS = 5


def main():
    print(f"[edge] Iniciant pipeline per a la càmera {config.CAMERA_ID}...")

    capture = CameraCapture(config.SOURCE).start()
    motion_detector = MotionDetector(min_area=config.MOTION_MIN_AREA)
    bird_classifier = BirdClassifier(
        weights_path=config.YOLO_WEIGHTS,
        conf_threshold=config.YOLO_CONF_THRESHOLD,
        target_class=config.BIRD_CLASS_NAME,
    )
    cropper = DetectionCropper(output_dir=config.CROPS_DIR)
    backend = BackendClient(
        base_url=config.BACKEND_URL,
        camera_id=config.CAMERA_ID,
        publish_token=config.PUBLISH_TOKEN,
    )
    publisher = StreamPublisher(
        rtsp_url=config.mediaserver_publish_url,
        width=config.STREAM_WIDTH,
        height=config.STREAM_HEIGHT,
    ).start()

    last_detection_sent_at = 0.0

    try:
        while True:
            frame = capture.read()
            if frame is None:
                time.sleep(0.05)
                continue

            # --- Fase 1: Model 1 (moviment) ---
            has_motion, _boxes = motion_detector.detect(frame)

            if has_motion:
                # --- Fase 2: Model 2 (YOLO, només si hi ha moviment) ---
                detections = bird_classifier.classify(frame)

                now = time.time()
                if detections and (now - last_detection_sent_at) > DETECTION_COOLDOWN_SECONDS:
                    best = max(detections, key=lambda d: d.confidence)

                    # --- Cropping + enviament ---
                    crop_path = cropper.crop(frame, best.box)

                    try:
                        result = backend.send_frame_detection(
                            image_path=crop_path,
                            detected_at=cropper.timestamp_iso(),
                        )
                        print(f"[edge] Detecció enviada: {result}")
                        last_detection_sent_at = now
                    except Exception as exc:
                        print(f"[edge] Error enviant detecció: {exc}")

                    # Dibuixem la caixa per al stream visual (opcional)
                    x1, y1, x2, y2 = best.box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # --- Publicació del stream en baixa resolució (sempre) ---
            resized = cv2.resize(frame, (config.STREAM_WIDTH, config.STREAM_HEIGHT))
            publisher.push_frame(resized)

    except KeyboardInterrupt:
        print("[edge] Aturant pipeline...")
    finally:
        capture.stop()
        publisher.stop()


if __name__ == "__main__":
    main()
