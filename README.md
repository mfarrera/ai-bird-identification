# AI Bird Identification Project

A citizen science platform for AI-based bird identification using camera streams. Detects, tracks, and classifies birds in real time and shares observations via a web interface.

## How to build 

The code has two parts: Backend Frontend. They need to be started separately, not necessarily in the same host, but configuration changes would be required. The current instructions assume that you start both services on the same host.

### Backend – FastAPI

- Python 3
- FastAPI
- PostgreSQL
- Docker
- Docker Compose

---

#### Instaling dependencies

Inside the /backend folder type:

```bash
pip install -r requirements.txt
```

---

#### Deploying the backend 

To deploy the backend type the following comands from the root project.

```bash
docker compose up --build
```

It deploys:

- The backend (FastAPI)
- The database (PostgreSQL)

---

#### Running the application 

- Backend:
  http://localhost:8000

- API Docs (Swagger):
  http://localhost:8000/docs

---

#### Relevant Environment variables 

- `JWT_SECRET`: obligatorio en producción.
- `FRONTEND_ORIGINS`: permite lista separada por comas o JSON array.
- `JOB_RETENTION_SECONDS`: tiempo en segundos para mantener jobs en memoria.
- `JOB_MAX_ENTRIES`: límite máximo de jobs en memoria.

La cola/estado de análisis de vídeo se persiste en PostgreSQL (`video_jobs`), y al reiniciar backend se reanudan jobs en `queued/running`.

---

#### Backend Shutdown

To stop the containers:

```bash
docker compose down
```

Stop containers and clean up (delete volumes):

```bash
docker compose down -v
```

### Frontend del Detector d’Aus — React + Vite + Tailwind CSS

Frontend consists of a simple web application build with React, Vite and Tailwind CSS. It allows users to upload images and videos
sending them to the backend for AI identificatin and visualize results. It also has the funcionality of live streaming with AI identification.

#### Requirements

- Node.js 18+
- npm o pnpm

#### Installation

```bash
npm install
```

#### Start up

```bash
npm run dev
```

Frontend should be available at port 5173
http://localhost:5173


