"""
Feina de la cua 'fase2': identificar l'espècie amb el Model 2 (CNN).

Encara no existeix cap CNN entrenat (només hi ha els pesos de YOLO,
que és el Model 1) — així que, de moment, aquest job és un STUB: no fa
cap inferència real, només marca la detecció com a 'done' perquè el
pipeline no es quedi penjat esperant una fase que no pot completar-se.

Quan hi hagi el CNN: substituir el cos d'aquesta funció per baixar la
imatge (detections.url, que després de fase1 ja és el retall), córrer
el model, i INSERT INTO species_detected (species_id, detection_id,
confidence) amb el resultat.
"""

from database import get_connection


def process_phase2(detection_id: int):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # TODO: quan hi hagi el CNN d'identificació d'espècie:
        # 1. Llegir detections.url (el retall) i baixar-lo de MinIO.
        # 2. Córrer el model, obtenir species_id + confidence.
        # 3. INSERT INTO species_detected (species_id, detection_id, confidence)
        #    VALUES (%s, %s, %s)

        cur.execute(
            "UPDATE detections SET status = 'done' WHERE id = %s",
            (detection_id,)
        )
        conn.commit()

    finally:
        cur.close()
        conn.close()
