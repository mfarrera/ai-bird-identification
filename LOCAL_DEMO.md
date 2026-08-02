# Demo local — tot el flux funcionant sense servidor

Aquesta guia aixeca **Postgres + Backend + Mediaserver + Edge** amb Docker, i el
**Frontend** el corres directament amb `pnpm` (ja apunta a `127.0.0.1:8000`
per codi, així que no cal tocar res).

```
┌────────────┐  push RTSP   ┌─────────────┐  auth webhook  ┌─────────┐
│    Edge     │ ───────────> │ Mediaserver │ ─────────────> │ Backend │
│ (Docker)    │ <─────────── │  (MediaMTX) │ <───────────── │(Docker) │
└────────────┘  detections   └─────────────┘                └────┬────┘
                    API                                            │
                                                              ┌─────▼───┐
      Navegador (pnpm dev, localhost:5173) ── HLS :8888 ─>   │ Postgres│
      consulta l'API a localhost:8000                        └─────────┘
```

## 1. Requisits al host

- Docker + Docker Compose
- `ffmpeg` (només si vols generar el vídeo de prova sintètic)
- Node.js + `pnpm` (per al frontend)

## 2. Vídeo de prova per a l'Edge

Com no disposes de material real d'ocells, tens dues opcions:

**Opció A — vídeo sintètic (ràpid, valida només moviment)**
```bash
./infra/scripts/generate_test_video.sh
```
Genera `apps/edge/media/sample.mp4` amb un objecte movent-se. Vàlid per
comprovar tot el pipeline de moviment → crop → API → BBDD, però YOLO no el
classificarà com a "bird" (és una forma sintètica).

**Opció B — webcam en directe (recomanat per veure el flux SENCER)**

Al `docker-compose.yml`, canvia temporalment:
```yaml
CAMERA_SOURCE: "0"
BIRD_CLASS_NAME: person
```
i afegeix accés al dispositiu de vídeo del host al servei `edge`:
```yaml
devices:
  - /dev/video0:/dev/video0
```
(Linux only — a macOS/Windows amb Docker Desktop l'accés a webcam des d'un
contenidor no funciona bé; en aquest cas és millor córrer `apps/edge` fora
de Docker, amb un venv local, seguint el README de `apps/edge`.)

Movent-te davant la càmera veuràs deteccions reals de principi a fi.

## 3. Aixecar la infraestructura

```bash
docker compose up --build
```

Comprova:
- Backend: http://localhost:8000/docs (Swagger de FastAPI)
- Mediaserver (HLS): es publicarà a `http://localhost:8888/cam1/index.m3u8` quan
  l'Edge comenci a publicar
- Logs de l'Edge: `docker compose logs -f edge` (o `docker compose logs -f mediaserver`)
  — hauries de veure `[edge] Detecció enviada: ...` quan detecti moviment + classe objectiu

La primera arrencada de `edge` trigarà una mica més: `ultralytics` descarrega
els pesos de YOLO (`yolov8n.pt`) automàticament dins del volum `models/`.

## 4. Aixecar el frontend

```bash
cd apps/frontend
pnpm install
pnpm dev
```

Obre `http://localhost:5173`. Inicia sessió amb un usuari real del `backup.sql`:

- **mail**: `admin@gmail.com`
- **password**: `admin`

(la resta d'usuaris del dump —`hola@gmail.com`, `1@gmail.com`... — tenen contrasenyes igual de trivials en text pla; és l'esquema real que m'has passat, no l'he modificat)

## 5. Què hauries de poder ensenyar

1. **Login** amb l'usuari admin sembrat.
2. **Llistar càmeres** (`LlistarCameresAdmin`) → hi surten les 3 càmeres del
   dump. La `1` és la que fa servir el worker Edge per publicar
   (`PUBLISH_TOKEN=secreto_edge_123` al `docker-compose.yml`, igual que
   `secreto_edge_123` al `backup.sql`). El camp `url` de la taula (p. ex.
   `rtsp://192.168.1.20:8554/cam1`) és només informatiu — la ruta real de
   publicació/reproducció sempre és `cam{id}`, construïda pel backend a
   partir de `STREAM_BASE_URL` (variable `hls_url` a `/api/cameras/{id}/stream`).
3. **Veure l'stream en directe** (`VeureStreamAdmin` / `ProvaTokenStream`):
   el vídeo que l'Edge està publicant en baixa resolució, via HLS.
4. **Deteccions**: consulta `GET http://localhost:8000/docs#/default/get_next_detection_to_validate`
   (o l'endpoint equivalent) per veure les deteccions que l'Edge ha anat
   enviant, amb la imatge retallada servida a
   `http://localhost:8000/uploads/detections/<fitxer>.jpg`.

## 6. Aturar-ho tot

```bash
docker compose down        # atura els contenidors
docker compose down -v     # + esborra la BBDD i els uploads (reset total)
```

## Notes / limitacions d'aquesta demo

- Aquesta demo restaura directament el teu `backup.sql` real (sanejat de
  `OWNER TO` / `GRANT` a rols que no existeixen en un contenidor nou, i sense
  els `\restrict`/`\unrestrict` de psql 17+). Per tant l'`id`, el
  `publish_token` (`secreto_edge_123`) i l'estat de la càmera `1` són
  exactament els que ja tenies a la teva BBDD, no dades inventades.
- Mediaserver (MediaMTX) corre sense TLS ni WebRTC per simplicitat; el diagrama original
  preveu WebRTC per al Media Server, no implementat en aquesta demo.
- La contrasenya de l'usuari sembrat es guarda en text pla perquè així ho fa
  actualment el backend (pendent d'afegir hashing).
