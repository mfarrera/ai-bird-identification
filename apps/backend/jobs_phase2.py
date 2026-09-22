"""
Feina de la cua 'fase2': identificar l'especie amb el Model 2
(YOLO especialitzat, bestgen.pt -- 101 especies, cadascuna es la seva
propia classe, no cal cap CNN separat a sobre).

Aquest moduel NOMES es carrega dins del contenidor worker-phase2 (que
instal.la ultralytics/opencv) -- el backend (API) no els necessita.
"""

import os
import tempfile

import requests
from ultralytics import YOLO

from database import get_connection
from storage import get_url

SPECIES_MODEL_PATH = os.getenv("SPECIES_MODEL_PATH", "/app/models/bestgen.pt")
SPECIES_CONF_THRESHOLD = float(os.getenv("SPECIES_CONF_THRESHOLD", "0.5"))

# Carreguem el model un sol cop per proces worker, no a cada feina.
_model = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(SPECIES_MODEL_PATH)
    return _model


def _get_or_create_species_id(cur, species_name: str) -> int:
    """
    Busca l'especie per nom (no per index -- aixi no depenem que
    l'ordre de la taula 'species' coincideixi amb el del model). Si
    per algun motiu no existeix (per exemple, no s'ha aplicat encara
    la migracio de seed), la crea al vol perque el job no falli.
    """

    cur.execute("SELECT id FROM species WHERE name = %s", (species_name,))
    row = cur.fetchone()

    if row is not None:
        return row[0]

    cur.execute(
        "INSERT INTO species (name, url) VALUES (%s, '') RETURNING id",
        (species_name,)
    )
    return cur.fetchone()[0]


def process_phase2(detection_id: int):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT url FROM detections WHERE id = %s", (detection_id,))
        row = cur.fetchone()

        if row is None:
            return

        object_name = row[0]

        # Igual que a fase1: generem la URL amb el MINIO_ENDPOINT propi
        # d'aquest worker, no reutilitzem cap URL generada per un altre proces.
        file_url = get_url(object_name)

        response = requests.get(file_url, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        model = _get_model()

        try:
            results = model.predict(tmp_path, conf=SPECIES_CONF_THRESHOLD, verbose=False)[0]
        finally:
            os.remove(tmp_path)

        # bestgen.pt detecta i classifica alhora: cada caixa ja porta
        # la seva especie. Ens quedem amb la de mes confianca.
        best_box = None
        best_conf = 0.0

        for box in results.boxes:
            conf = float(box.conf[0])
            if conf > best_conf:
                best_conf = conf
                best_box = box

        if best_box is None:
            # Cap especie per sobre del llindar de confianca: acabem
            # igualment (no cal cap fase mes despres d'aquesta).
            cur.execute(
                "UPDATE detections SET status = 'done' WHERE id = %s",
                (detection_id,)
            )
            conn.commit()
            return

        class_id = int(best_box.cls[0])
        species_name = model.names[class_id]

        species_id = _get_or_create_species_id(cur, species_name)

        cur.execute("""
            INSERT INTO species_detected (species_id, detection_id, confidence)
            VALUES (%s, %s, %s)
            ON CONFLICT (species_id, detection_id) DO NOTHING
        """, (species_id, detection_id, best_conf))

        cur.execute(
            "UPDATE detections SET status = 'done' WHERE id = %s",
            (detection_id,)
        )
        conn.commit()

    finally:
        cur.close()
        conn.close()
