# TFG — Plataforma de videovigilància amb detecció d'ocells

Plataforma per gestionar càmeres, usuaris i comunitats, amb un pipeline
de detecció automàtica (moviment → YOLO → identificació d'espècie) a
partir del vídeo que publiquen els dispositius Edge.

## Arquitectura

```
Edge (YOLO local) ──RTSP──> Mediaserver (MediaMTX) ──HLS──> Frontend
       │                           │
       │ push detecció+imatge      │ auth webhook
       ▼                           ▼
    Backend (FastAPI) ───────── Postgres (natiu, fora de Docker)
       │
       ▼
     MinIO (imatges/vídeos de deteccions)
```

Serveis a `docker-compose.yml`: **backend**, **mediaserver**, **edge**,
**minio**, **frontend**, **redis**, **worker-phase1**, **worker-phase2**.
El **Postgres NO corre a Docker** — és el teu Postgres natiu del host,
amb les teves dades reals; el backend hi accedeix amb `network_mode:
host`.

El pipeline de detecció és asíncron amb dues cues de Redis (RQ):
`fase1` (YOLO — troba l'ocell i el retalla) i `fase2` (CNN —
identifica l'espècie, encara en stub). El **backend** només encua
feina; qui la processa són **worker-phase1** i **worker-phase2**, que
poden escalar-se de forma independent.

## Requisits previs

- Docker Engine + el plugin de Compose v2 (`docker compose version` ha
  de funcionar; si dona "unknown command", instal·la'l manualment —
  veure [Notes](#notes--problemes-habituals))
- Postgres instal·lat i corrent al host (fora de Docker)
- `ffmpeg` (per generar un vídeo de prova si no tens material real)
- Python 3.10+ i `pip` (per al venv del backend, usat només per
  `pip install` — el backend en si corre dins de Docker)

## 1. Base de dades

Crea l'usuari i la base de dades al teu Postgres natiu (substitueix
`usuari`/`contrasenya` pels que vulguis):

```bash
sudo -u postgres psql -c "CREATE USER usuari WITH PASSWORD 'contrasenya';"
sudo -u postgres psql -c "CREATE DATABASE tfgdb OWNER usuari;"
```

No cal crear cap taula a mà — el backend aplica l'esquema
automàticament en arrencar (veure `apps/backend/migrations/`).

## 2. Configuració del backend

```bash
cd apps/backend
cp .env.example .env
```

Edita `.env` amb el `DATABASE_URL` (usuari/contrasenya/BBDD que has
creat al pas 1) i la resta de valors (com a mínim `SECRET_KEY`; el SMTP
només cal si vols que funcionin els correus d'acceptació/denegació de
càmeres).

## 3. Vídeo de prova per a l'Edge

Si no tens material real d'ocells, genera un vídeo sintètic (una caixa
movent-se, vàlid per provar el pipeline de moviment però YOLO no el
classificarà com a "bird"):

```bash
chmod +x infra/scripts/generate_test_video.sh
./infra/scripts/generate_test_video.sh
```

Això crea `apps/edge/media/sample.mp4`. Alternativament, posa-hi el teu
propi vídeo amb aquest mateix nom, o munta una webcam real seguint les
notes del `apps/edge/README.md`.

També assegura't que hi ha els pesos de YOLO a
`apps/edge/models/yolov8n.pt` (es pot descarregar amb `yolo` o des de
[ultralytics](https://github.com/ultralytics/assets/releases)).

## 4. Aixecar-ho tot

```bash
docker compose up --build
```

Això construeix i aixeca **backend**, **mediaserver**, **edge**,
**minio** i **frontend**. La primera vegada trigarà una mica (el backend
instal·la dependències i el edge instal·la YOLO/PyTorch, que pesen).

En el log del backend hauries de veure que aplica la migració inicial
de l'esquema (`[migrations] Aplicant 0001_initial_schema.sql...`).

## 5. Accessos

| Servei | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend (Swagger) | http://localhost:8000/docs |
| Mediaserver (HLS) | http://localhost:8888 |
| MinIO (consola web) | http://localhost:9001 (usuari `minioadmin` / contrasenya `minioadmin123`) |

## 6. Aturar-ho

```bash
docker compose down
```

(el Postgres és fora de Docker, així que les teves dades no es toquen
amb aquest ni cap altre `docker compose down`)

## Estructura del projecte

```
apps/
  backend/      FastAPI + psycopg, connecta al Postgres natiu del host
  frontend/     React + Vite
  mediaserver/  MediaMTX (RTSP -> HLS), autenticació delegada al backend
  edge/         Captura + YOLO local + publicació RTSP + enviament de deteccions
infra/
  scripts/      Utilitats (p. ex. generar vídeo de prova)
```

## Com arriben els workers a la teva BBDD (`DB_HOST_OVERRIDE`)

El **backend** corre amb `network_mode: host`, així que dins seu
`localhost` és literalment el teu host — el `DATABASE_URL` de
`apps/backend/.env` (amb `localhost`) funciona tal qual.

Els **workers** (`worker-phase1`, `worker-phase2`) **no** fan servir
`network_mode: host` — corren a la xarxa normal de Docker, aïllats. Si
hi intentessin connectar a `localhost:5432`, apuntarien al propi
contenidor del worker, no al teu Postgres. Per això necessiten
`host.docker.internal` (el nom que Docker resol a la IP del host) en
comptes de `localhost`.

En lloc d'escriure una `DATABASE_URL` diferent (amb usuari/contrasenya
hardcodejats) al `docker-compose.yml` — que es puja a git i trencaria
per a qualsevol altra persona amb credencials diferents  —
els workers reben només:

```yaml
DB_HOST_OVERRIDE: host.docker.internal
```

I `apps/backend/database.py` fa aquesta substitució en temps
d'execució:

```python
DB_HOST_OVERRIDE = os.getenv("DB_HOST_OVERRIDE")
if DB_HOST_OVERRIDE and DATABASE_URL:
    DATABASE_URL = re.sub(r"@[^:/@]+:", f"@{DB_HOST_OVERRIDE}:", DATABASE_URL, count=1)
```

Això canvia només la part de l'amfitrió de la URL (el que hi ha entre
`@` i `:`), mantenint l'usuari i la contrasenya que ja hi ha a `.env`
intactes. Resultat:

- El **backend** no defineix `DB_HOST_OVERRIDE` → `DATABASE_URL` es fa
  servir tal qual (amb `localhost`).
- Els **workers** sí la defineixen → en temps d'execució acaben usant
  la mateixa `DATABASE_URL` del teu `.env` però amb
  `host.docker.internal` en lloc de `localhost`.
- Si algú clona el repo amb un `DATABASE_URL` diferent (altre
  usuari/contrasenya/BBDD), li funciona igual sense tocar res: només
  es canvia l'amfitrió, mai les credencials.

Pel mateix motiu, els workers també sobreescriuen `MINIO_ENDPOINT:
minio:9000` (nom del servei dins la xarxa de Docker) en comptes del
`localhost:9000` que fa servir el backend.

## Afegir canvis a l'esquema de la BBDD

Crea un fitxer nou a `apps/backend/migrations/`, numerat en ordre
(`0002_el-que-sigui.sql`). Es SQL normal — no cal que sigui idempotent,
el sistema garanteix que cada fitxer s'executa com a molt un cop per
BBDD (ho porta el compte la taula `schema_migrations`). S'aplica sol la
propera vegada que arranqui el contenidor del backend.

## Notes / problemes habituals

- **`docker compose` no és una ordre reconeguda**: als repositoris
  d'Ubuntu no sempre hi ha el plugin de Compose v2. Instal·la'l a mà:
  ```bash
  mkdir -p ~/.docker/cli-plugins
  curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
  chmod +x ~/.docker/cli-plugins/docker-compose
  ```
- **`permission denied` al soquet de Docker**: el teu usuari no és al
  grup `docker` — `sudo usermod -aG docker $USER` i torna a iniciar
  sessió (o `newgrp docker`).
- **Carpetes creades per Docker com a `root`** (p. ex.
  `apps/edge/media`, `models`, `crops` si mai les crea Docker abans que
  tu): `sudo chown -R $USER:$USER apps/edge/media apps/edge/models apps/edge/crops`.
- Els `.dockerignore` de `apps/backend`, `apps/edge` i `apps/frontend`
  exclouen `venv/`/`node_modules/` del build — no cal (ni convé) que hi
  siguin, el propi `Dockerfile` instal·la les dependències dins del
  contenidor.
