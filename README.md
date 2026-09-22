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
    Backend (FastAPI) ───────── Postgres (Docker, dades persistents)
       │
       ▼
     MinIO (imatges/vídeos de deteccions)
```

Serveis a `docker-compose.yml`: **backend**, **mediaserver**, **edge**,
**minio**, **frontend**, **redis**, **worker-phase1**, **worker-phase2**,
**postgres**, **pgadmin**. Totes les dades (Postgres i MinIO) persisteixen
en volums de Docker entre reinicis.

El pipeline de detecció és asíncron amb dues cues de Redis (RQ):
`fase1` (YOLO — troba l'ocell i el retalla) i `fase2` (YOLO especialitzat
— identifica l'espècie concreta, 101 classes). El **backend** només
encua feina; qui la processa són **worker-phase1** i **worker-phase2**,
que poden escalar-se de forma independent.

## Requisits previs

- Docker Engine + el plugin de Compose v2 (`docker compose version` ha
  de funcionar; si dona "unknown command", instal·la'l manualment —
  veure [Notes](#notes--problemes-habituals))
- `ffmpeg` (per generar un vídeo de prova si no tens material real)
- Python 3.10+ i `pip` (per al venv del backend, usat només per
  `pip install` — el backend en si corre dins de Docker)

---

## Primer cop (clonar el repo des de zero)

### 1. Base de dades

Postgres corre com un servei més de `docker-compose.yml` (`postgres`),
amb dades persistents en un volum de Docker (`postgres_data`) — no cal
instal·lar-lo ni configurar-lo a mà. La primera vegada que aixequis el
projecte, es crea buit i el backend hi aplica l'esquema automàticament
(veure [Migracions de la BBDD](#migracions-de-la-bbdd) més avall).

Credencials per defecte (definides a `docker-compose.yml`, pensades
només per a desenvolupament local — canvia-les si vas a exposar això
en cap altre entorn): usuari `tfg`, contrasenya `tfg_dev_password`,
base de dades `tfgdb`.

### 2. Configuració del backend

```bash
cd apps/backend
cp .env.example .env
```

Edita `.env` amb el `DATABASE_URL` (per defecte
`postgresql://tfg:tfg_dev_password@localhost:5432/tfgdb`, si no has
canviat les credencials del pas 1) i la resta de valors (com a mínim
`SECRET_KEY`; el SMTP només cal si vols que funcionin els correus
d'acceptació/denegació de càmeres).

### 3. Vídeo de prova per a l'Edge

Si no tens material real d'ocells, genera un vídeo sintètic (una caixa
movent-se, vàlid per provar el pipeline de moviment però YOLO no el
classificarà com a "bird"):

```bash
chmod +x infra/scripts/generate_test_video.sh
./infra/scripts/generate_test_video.sh
```

Això crearà `apps/edge/media/sample.mp4`. Alternativament, posa-hi el teu
propi vídeo amb aquest mateix nom, o munta una webcam real seguint les
notes del `apps/edge/README.md`.

### 4. Aixecar-ho tot

```bash
docker compose up --build
```

Això construeix i aixeca **tots** els serveis (backend, mediaserver,
edge, minio, frontend, redis, worker-phase1, worker-phase2, postgres,
pgadmin). La primera vegada trigarà una mica (el backend instal·la
dependències i l'edge/workers instal·len YOLO/PyTorch, que pesen).

En el log del backend hauries de veure que aplica les migracions
inicials de l'esquema (`[migrations] Aplicant 0001_initial_schema.sql...`,
`0002_...`, `0003_...`).

### 5. Accessos

| Servei | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend (Swagger) | http://localhost:8000/docs |
| Mediaserver (HLS) | http://localhost:8888 |
| MinIO (consola web) | http://localhost:9001 (usuari `minioadmin` / contrasenya `minioadmin123`) |
| Postgres | `localhost:5432` (usuari `tfg` / contrasenya `tfg_dev_password` / BBDD `tfgdb`) |
| pgAdmin | http://localhost:5050 (usuari `admin@ocellwatch.com` / contrasenya `admin_dev_password`) |

### 6. Administrar la BBDD amb pgAdmin

`pgadmin` és un servei més de `docker-compose.yml`, ja apuntant al
`postgres` del projecte. Un cop aixecat (`docker compose up -d pgadmin`
si no vols aixecar-ho tot), entra a http://localhost:5050 amb
`admin@ocellwatch.com` / `admin_dev_password` (credencials de
desenvolupament, canvia-les si això surt mai del teu PC).

Per registrar el servidor de Postgres dins de pgAdmin (nomes cal la
primera vegada): botó dret sobre "Servers" -> Register -> Server. A la
pestanya "General" posa-li un nom qualsevol (p. ex. "TFG"). A la
pestanya "Connection":

| Camp | Valor |
|---|---|
| Host name/address | `postgres` (nom del servei, no `localhost`) |
| Port | `5432` |
| Maintenance database | `tfgdb` |
| Username | `tfg` |
| Password | `tfg_dev_password` |

### 7. Aturar-ho

```bash
docker compose down
```

(les dades de Postgres i MinIO viuen en volums de Docker — sobreviuen
a `docker compose down`. Si vols esborrar-les del tot, `docker compose
down -v`, però ves amb compte: això esborra les dades reals.)

---

## Actualitzar el projecte (`git pull`)

Un cop ja el tens tot muntat un primer cop, per agafar canvis nous
normalment només cal:

```bash
git pull
docker compose up -d --build
```

- `--build` reconstrueix només les imatges els fitxers de les quals
  han canviat (Docker cacheja per capes: si només has tocat
  `main.py`, per exemple, triga segons, no minuts) — és segur deixar-lo
  sempre encara que no sàpigues què ha canviat.
- Les migracions de BBDD noves (fitxers nous a
  `apps/backend/migrations/`) **s'apliquen soles**: cada vegada que
  arrenca el contenidor del backend, executa
  `apps/backend/run_migrations.py`, que compara contra la taula
  `schema_migrations` i només aplica els fitxers que encara no
  constaven com a aplicats. No cal (ni s'ha de) executar cap SQL a mà.
- Si `docker-compose.yml` ha afegit un servei nou (com va passar amb
  `worker-phase2`), el mateix `docker compose up -d --build` ja el
  construeix i l'aixeca; no cal cap pas extra.

## Estructura del projecte

```
apps/
  backend/         FastAPI + psycopg, connecta a Postgres (Docker)
                    + workers RQ (fase1/fase2) i les seves migracions
  frontend/        React + Vite
  mediaserver/     MediaMTX (RTSP -> HLS), autenticació delegada al backend
  edge/            Captura + YOLO local + publicació RTSP + enviament de deteccions
  model-ia-cloud/  Pesos dels models del cloud (yolov8n.pt, bestgen.pt)
infra/
  scripts/         Utilitats (p. ex. generar vídeo de prova)
```

## Com arriben els workers a la teva BBDD (`DB_HOST_OVERRIDE`)

El **backend** corre amb `network_mode: host`, així que dins seu
`localhost` és literalment el teu host — el `DATABASE_URL` de
`apps/backend/.env` (amb `localhost`) funciona tal qual.

Els **workers** (`worker-phase1`, `worker-phase2`) **no** fan servir
`network_mode: host` — corren a la xarxa normal de Docker, aïllats. Si
hi intentessin connectar a `localhost:5432`, apuntarien al propi
contenidor del worker, no a Postgres (encara que Postgres també corri
en un contenidor: cada contenidor és una xarxa aïllada, no es veuen
entre ells per `localhost`). Per això necessiten `host.docker.internal`
(el nom que Docker resol a la IP del host) en comptes de `localhost`.

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

## Migracions de la BBDD

Crea un fitxer nou a `apps/backend/migrations/`, numerat en ordre
(`0004_el-que-sigui.sql`). És SQL normal — no cal que sigui idempotent,
el sistema garanteix que cada fitxer s'executa com a molt un cop per
BBDD (ho porta el compte la taula `schema_migrations`). S'aplica sol la
propera vegada que arranqui el contenidor del backend (veure
[Actualitzar el projecte](#actualitzar-el-projecte-git-pull)).

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
