from fastapi import FastAPI, HTTPException, Query, Request, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from urllib.parse import parse_qs
from email.message import EmailMessage
from storage import upload_file, get_url
from queues import queue_fase1, queue_fase2

import psycopg
import os
import jwt
import smtplib
import uuid

import secrets


app = FastAPI()

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
STREAM_BASE_URL = os.getenv("STREAM_BASE_URL", "127.0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)
class MediaMTXAuthRequest(BaseModel):
    # Usuari enviat pel client, si n'hi ha
    user: str | None = None

    # Password enviada pel client, si n'hi ha
    password: str | None = None

    # Token enviat pel client, si n'hi ha
    token: str | None = None

    # IP del client que intenta accedir
    ip: str | None = None

    # Acció que vol fer: publish, read, playback, api, metrics o pprof
    action: str

    # Path del stream, per exemple "cam1"
    path: str | None = None

    # Protocol utilitzat: rtsp, rtmp, hls, webrtc, srt...
    protocol: str | None = None

    # Identificador intern de MediaMTX
    id: str | None = None

    # Query string rebuda, per exemple "jwt=abc123"
    query: str | None = None

class LoginData(BaseModel):
    # Correu electrònic de l'usuari que intenta iniciar sessió
    mail: str

    # Contrasenya escrita per l'usuari
    password: str

class UserRegister(BaseModel):
    mail: str
    password: str
    role: str
    privacity: str = "private"

class CameraCreate(BaseModel):
    # URL del stream de la càmera
    url: str

    # Id de l'usuari propietari de la càmera
    owner_id: int

    # Latitud de la ubicació de la càmera
    latitude: float

    # Longitud de la ubicació de la càmera
    longitude: float

class CameraUpdate(BaseModel):
    # Nova URL del stream de la càmera
    url: str

    # Nou propietari de la càmera
    owner_id: int

    # Nova latitud
    latitude: float

    # Nova longitud
    longitude: float

class CommunityCreate(BaseModel):
    # Nombre de la comunitat
    name: str

class CommunityMembersAdd(BaseModel):
    # Llista d'usuaris a afegir a la comunitat
    user_ids: list[int]

class CommunityCamerasAdd(BaseModel):
    # Llista de càmeres a associar a la comunitat
    camera_ids: list[int]

class CommunityLeaderUpdate(BaseModel):
    leader_id: int

class CameraRequestCreate(BaseModel):
    url: str
    latitude: float
    longitude: float

class CameraDecision(BaseModel):
    decision: str
    rejection_reason: str | None = None


def send_email(to_email: str, subject: str, body: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user or not smtp_password:
        raise RuntimeError("La configuració SMTP no està completa")

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)

def generate_session_token(user_id: int, mail: str, role: str, expires_minutes: int = 120):
    """
    Genera un JWT real per donar accés temporal a la sessió d'un usuari.

    Què inclou el token:
    - user_id: usuari que ha iniciat sessió
    - mail: correu electrònic de l'usuari
    - role: rol de l'usuari
    - exp: data d'expiració
    - iat: data de creació del token
    """

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expires_minutes)

    payload = {
        "user_id": user_id,
        "mail": mail,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp())
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token, expires_at
    

def generate_stream_token(user_id: int, camera_id: int, expires_minutes: int = 60):
    """
    Genera un JWT real per donar accés temporal a un stream.

    Què inclou el token:
    - user_id: usuari que demana accés
    - camera_id: càmera a la qual vol accedir
    - exp: data d'expiració
    - iat: data de creació del token
    """

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expires_minutes)

    payload = {
        "user_id": user_id,
        "camera_id": camera_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp())
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token, expires_at

@app.get("/api/users/me/cameras/most-viewed")
def get_most_viewed_cameras(request: Request, limit: int = 5):
    """
    Endpoint: GET /api/users/me/cameras/most-viewed

    Que fa:
    - Retorna les cameres que l'usuari connectat ha vist mes vegades
      (basat en la taula display), ordenades de mes a menys vistes.
    """
    payload = verify_token(request)
    user_id = payload.get("user_id")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.id, c.url, COUNT(d.id) AS views
            FROM display d
            JOIN camera c ON c.id = d.camera_id
            WHERE d.user_id = %s
            GROUP BY c.id, c.url
            ORDER BY views DESC, c.id
            LIMIT %s
        """, (user_id, limit))
        rows = cur.fetchall()
        return [{"id": r[0], "url": r[1], "views": r[2]} for r in rows]
    finally:
        cur.close()
        conn.close()


def verify_token(request: Request):
    """
    Llegeix el token de l'header Authorization, el valida
    i retorna el payload si és correcte.
    """

    authorization = request.headers.get("Authorization")

    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Falta la capçalera Authorization"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Format d'autorització incorrecte"
        )

    token = authorization.replace("Bearer ", "", 1)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="El token ha caducat"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="El token no és vàlid"
        )

def get_current_user(request: Request):
    """
    Valida el token i retorna les dades bàsiques de l'usuari autenticat.
    """

    payload = verify_token(request)

    return {
        "user_id": payload["user_id"],
        "mail": payload["mail"],
        "role": payload["role"]
    }

def require_admin(request: Request):
    """
    Comprova que l'usuari autenticat sigui admin.
    """

    user = get_current_user(request)

    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="No tens permisos d'administrador"
        )

    return user
    
def require_community_leader(community_id: int, request: Request) -> dict:
    """
    Comprova que l'usuari autenticat sigui el líder d'aquesta comunitat
    (els admins es poden saltar aquesta restricció).
    """

    user = get_current_user(request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT leader_id FROM community WHERE id = %s", (community_id,))
        row = cur.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="La comunitat no existeix")

        if user["role"] != "admin" and row[0] != user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="Només el líder de la comunitat pot fer aquesta acció"
            )
    finally:
        cur.close()
        conn.close()

    return user


def require_community_member(community_id: int, request: Request) -> dict:
    """
    Comprova que l'usuari autenticat sigui membre d'aquesta comunitat
    (els admins es poden saltar aquesta restricció).
    """

    user = get_current_user(request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM community WHERE id = %s", (community_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="La comunitat no existeix")

        if user["role"] != "admin":
            cur.execute("""
                SELECT 1 FROM community_member
                WHERE community_id = %s AND user_id = %s
            """, (community_id, user["user_id"]))

            if cur.fetchone() is None:
                raise HTTPException(
                    status_code=403,
                    detail="Has de ser membre de la comunitat per fer aquesta acció"
                )
    finally:
        cur.close()
        conn.close()

    return user


def get_current_user_role(request: Request):
    payload = verify_token(request)
    return payload["role_id"]


@app.get("/")
def root():
    return {"message": "Backend funcionant amb PostgreSQL"}

@app.post("/api/users/register")
def register_user(data: UserRegister):
    """
    Endpoint: POST /api/users/register

    Què fa:
    - Registra un nou usuari.
    - Comprova que no existeixi un altre usuari amb el mateix correu.
    - Comprova que el rol sigui vàlid.
    - Comprova que la privacitat sigui vàlida.
    - Crea l'usuari.
    """

    allowed_roles = ["admin", "user", "camera_user"]
    allowed_privacity = ["private", "community", "public"]

    if data.role not in allowed_roles:
        raise HTTPException(status_code=400, detail="El rol no és vàlid")

    if data.privacity not in allowed_privacity:
        raise HTTPException(status_code=400, detail="La privacitat no és vàlida")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id
            FROM users
            WHERE mail = %s
        """, (data.mail,))
        existing_user = cur.fetchone()

        if existing_user is not None:
            raise HTTPException(
                status_code=400,
                detail="Ja existeix un usuari amb aquest correu"
            )

        cur.execute("""
            INSERT INTO users (role, password_hash, mail, privacity)
            VALUES (%s, %s, %s, %s)
            RETURNING id, mail, role, created_at, privacity
        """, (
            data.role,
            data.password,
            data.mail,
            data.privacity
        ))

        row = cur.fetchone()
        conn.commit()

        return {
            "message": "Usuari creat correctament",
            "user": {
                "id": row[0],
                "mail": row[1],
                "role": row[2],
                "created_at": str(row[3]),
                "privacity": row[4]
            }
        }

    finally:
        cur.close()
        conn.close()


@app.post("/api/auth/login")
def login_user(data: LoginData):
    """
    Endpoint: POST /api/auth/login

    Què fa:
    - Comprova mail i contrasenya
    - Si són correctes, genera un token de sessió
    - Retorna el token i la informació bàsica de l'usuari
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, mail, password_hash, role, privacity
            FROM users
            WHERE mail = %s
        """, (data.mail,))

        row = cur.fetchone()

        if row is None:
            raise HTTPException(
                status_code=401,
                detail="Usuari o contrasenya incorrectes"
            )

        user_id = row[0]
        user_mail = row[1]
        stored_password = row[2]
        role = row[3]
        privacity = row[4]

        if stored_password != data.password:
            raise HTTPException(
                status_code=401,
                detail="Usuari o contrasenya incorrectes"
            )

        token, expires_at = generate_session_token(
            user_id=user_id,
            mail=user_mail,
            role=role
        )

        return {
            "message": "Login correcte",
            "token": token,
            "expires": expires_at.isoformat(),
            "user": {
                "id": user_id,
                "mail": user_mail,
                "role": role,
                "privacity": privacity
            }
        }

    finally:
        cur.close()
        conn.close()


@app.post("/api/auth/refresh")
def refresh_session(request: Request):
    """
    Endpoint: POST /api/auth/refresh

    Que fa:
    - Sessio "lliscant": si el token de sessio actual encara es valid,
      en genera un de nou amb una altra finestra de 2 hores. Mentre
      l'usuari segueixi actiu (obrint pagines) abans que caduqui el
      token, el frontend el va renovant sol i la sessio no arriba mai
      a caducar de veritat.
    - Si el token ja ha caducat, aquesta crida tambe falla (401) — cal
      tornar a fer login. No hi ha cap "refresh token" separat: es fa
      servir el mateix token, nomes cal cridar aixo abans que caduqui.
    """

    payload = verify_token(request)

    token, expires_at = generate_session_token(
        user_id=payload["user_id"],
        mail=payload["mail"],
        role=payload["role"]
    )

    return {
        "token": token,
        "expires": expires_at.isoformat()
    }




    ##############camara##############

@app.post("/api/cameras/requests")
def request_camera(data: CameraRequestCreate, request: Request):
    """
    Crea una sol·licitud de càmera amb estat pending.
    L'owner s'obté del token de sessió.
    """

    payload = verify_token(request)
    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="El token no conté user_id"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id
            FROM users
            WHERE id = %s
        """, (user_id,))

        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="L'usuari no existeix"
            )

        cur.execute("""
            INSERT INTO camera (
                url,
                owner_id,
                latitude,
                longitude,
                camera_status
            )
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING
                id,
                url,
                owner_id,
                latitude,
                longitude,
                camera_status
        """, (
            data.url,
            user_id,
            data.latitude,
            data.longitude
        ))

        row = cur.fetchone()
        conn.commit()

        return {
            "message": "Sol·licitud de càmera creada correctament",
            "camera": {
                "id": row[0],
                "url": row[1],
                "owner_id": row[2],
                "latitude": str(row[3]),
                "longitude": str(row[4]),
                "camera_status": row[5]
            }
        }

    finally:
        cur.close()
        conn.close()

@app.get("/api/admin/camera-requests")
def get_pending_camera_requests(request: Request):
    payload = require_admin(request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                c.id,
                c.url,
                c.latitude,
                c.longitude,
                c.camera_status,
                c.owner_id,
                u.mail
            FROM camera c
            JOIN users u ON u.id = c.owner_id
            WHERE c.camera_status = 'pending'
            ORDER BY c.id ASC
        """)

        rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "url": row[1],
                "latitude": str(row[2]),
                "longitude": str(row[3]),
                "camera_status": row[4],
                "owner_id": row[5],
                "owner_mail": row[6]
            }
            for row in rows
        ]

    finally:
        cur.close()
        conn.close()

@app.put("/api/admin/cameras/{camera_id}/decision")
def review_camera_request(
    camera_id: int,
    data: CameraDecision,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Accepta o denega una sol·licitud de càmera.

    Si s'accepta:
    - genera publish_token;
    - canvia l'estat a accepted;
    - envia les credencials de publicació per correu.

    Si es denega:
    - canvia l'estat a denied;
    - guarda el motiu;
    - envia un correu a l'usuari.
    """

    payload = require_admin(request)

    admin_id = payload.get("user_id")

    if data.decision not in ["accepted", "denied"]:
        raise HTTPException(
            status_code=400,
            detail="La decisió ha de ser accepted o denied"
        )

    if data.decision == "denied" and not data.rejection_reason:
        raise HTTPException(
            status_code=400,
            detail="Cal indicar el motiu de denegació"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                c.id,
                c.camera_status,
                c.owner_id,
                u.mail
            FROM camera c
            JOIN users u ON u.id = c.owner_id
            WHERE c.id = %s
            FOR UPDATE
        """, (camera_id,))

        camera_row = cur.fetchone()

        if camera_row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        current_status = camera_row[1]
        owner_mail = camera_row[3]

        if current_status != "pending":
            raise HTTPException(
                status_code=409,
                detail="Aquesta sol·licitud ja ha estat revisada"
            )

        now = datetime.now(timezone.utc)

        if data.decision == "accepted":
            publish_token = secrets.token_urlsafe(32)

            cur.execute("""
                UPDATE camera
                SET camera_status = 'accepted',
                    publish_token = %s,
                    rejection_reason = NULL,
                    reviewed_at = %s,
                    reviewed_by = %s
                WHERE id = %s
            """, (
                publish_token,
                now,
                admin_id,
                camera_id
            ))

            conn.commit()

            cloud_host = os.getenv("CLOUD_HOST", "localhost")
            cloud_rtsp_port = os.getenv("CLOUD_RTSP_PORT", "8554")

            rtsp_url = (
                f"rtsp://{camera_id}:{publish_token}"
                f"@{cloud_host}:{cloud_rtsp_port}/cam{camera_id}"
            )

            email_body = f"""
La teva càmera amb identificador {camera_id} ha estat acceptada.

Credencials de publicació:

CAMERA_ID={camera_id}
CAMERA_TOKEN={publish_token}
RTSP_URL={rtsp_url}

Exemple amb Docker:

docker run --rm \\
  -e CAMERA_ID={camera_id} \\
  -e CAMERA_TOKEN="{publish_token}" \\
  -e RTSP_URL="{rtsp_url}" \\
  yourorg/birdcam-agent

Exemple amb FFmpeg:

ffmpeg -f dshow -i video="NOM_DE_LA_CAMERA" \\
  -c:v libx264 -f rtsp "{rtsp_url}"

No comparteixis el CAMERA_TOKEN. Aquesta credencial només permet publicar
el stream corresponent a aquesta càmera.
""".strip()

            background_tasks.add_task(
                send_email,
                owner_mail,
                "Càmera acceptada",
                email_body
            )

            return {
                "message": "Càmera acceptada correctament",
                "camera_id": camera_id,
                "camera_status": "accepted"
            }

        cur.execute("""
            UPDATE camera
            SET camera_status = 'denied',
                publish_token = NULL,
                rejection_reason = %s,
                reviewed_at = %s,
                reviewed_by = %s
            WHERE id = %s
        """, (
            data.rejection_reason,
            now,
            admin_id,
            camera_id
        ))

        conn.commit()

        email_body = f"""
La sol·licitud de la càmera amb identificador {camera_id} ha estat denegada.

Motiu:

{data.rejection_reason}
""".strip()

        background_tasks.add_task(
            send_email,
            owner_mail,
            "Sol·licitud de càmera denegada",
            email_body
        )

        return {
            "message": "Càmera denegada correctament",
            "camera_id": camera_id,
            "camera_status": "denied",
            "rejection_reason": data.rejection_reason
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


@app.post("/api/cameras")
def create_camera(camera: CameraCreate):
    """
    Endpoint: POST /api/cameras

    Què fa:
    - Crea una nova càmera a la base de dades.
    - Comprova que l'usuari propietari (owner_id) existeixi.
    - Guarda la URL del stream i la ubicació de la càmera.

    Què rep al body (JSON):
    {
        "url": "rtsp://192.168.1.50:554/stream",
        "owner_id": 1,
        "latitude": 41.23345678,
        "longitude": 1.72876543
    }

    Què retorna si va bé:
    {
        "message": "Càmera creada correctament",
        "camera": {
            "id": 3,
            "url": "rtsp://192.168.1.50:554/stream",
            "owner_id": 1,
            "latitude": 41.23345678,
            "longitude": 1.72876543
            "publish_token": "sh4jkj345kd433jdj18a7d9wls72sa81"
        }
    }

    Què retorna si va malament:
    - 400 si l'owner_id no existeix
    """

    # Obrim connexió amb PostgreSQL
    conn = get_connection()
    cur = conn.cursor()

    try:
        publish_token = secrets.token_urlsafe(32)

        cur.execute("""
            INSERT INTO camera (url, owner_id, latitude, longitude, publish_token)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, url, owner_id, latitude, longitude, publish_token
        """, (
            data.url,
            data.owner_id,
            data.latitude,
            data.longitude,
            publish_token
        ))

        row = cur.fetchone()
        conn.commit()

        return {
            "message": "Càmera creada correctament",
            "camera": {
                "id": row[0],
                "url": row[1],
                "owner_id": row[2],
                "latitude": str(row[3]),
                "longitude": str(row[4])
            },
            "publish_credentials": {
                "camera_id": row[0],
                "publish_token": row[5]
            }
        }

    finally:
        cur.close()
        conn.close()
    

@app.get("/api/cameras")
def get_cameras():
    """
    Endpoint: GET /api/cameras

    Què fa:
    - Retorna la llista de totes les càmeres registrades a la base de dades.

    Què rep:
    - No rep body.

    Què retorna si va bé:
    [
        {
            "id": 1,
            "url": "rtsp://192.168.1.50:554/stream",
            "owner_id": 1,
            "latitude": 41.23345678,
            "longitude": 1.72876543
        }
    ]
    """

    # Obrim connexió amb PostgreSQL
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Consultem totes les càmeres ordenades pel seu id
        cur.execute("""
            SELECT id, url, owner_id, latitude, longitude
            FROM camera
            ORDER BY id
        """)

        rows = cur.fetchall()

        # Convertim les files en una llista de diccionaris
        cameras = []
        for row in rows:
            cameras.append({
                "id": row[0],
                "url": row[1],
                "owner_id": row[2],
                "latitude": float(row[3]),
                "longitude": float(row[4])
            })

        return cameras

    finally:
        # Tanquem cursor i connexió sempre
        cur.close()
        conn.close()

@app.get("/api/cameras/{camera_id}")
def get_camera_by_id(camera_id: int):
    """
    Endpoint: GET /api/cameras/{camera_id}

    Què fa:
    - Busca una càmera concreta a partir del seu id.
    - Si existeix, la retorna.
    - Si no existeix, retorna error 404.

    Què rep:
    - camera_id a la URL.

    Exemple:
    GET /api/cameras/3

    Què retorna si va bé:
    {
        "id": 3,
        "url": "rtsp://192.168.1.50:554/stream",
        "owner_id": 1,
        "latitude": 41.23345678,
        "longitude": 1.72876543
    }

    Què retorna si va malament:
    - 404 si la càmera no existeix
    """

    # Obrim connexió amb PostgreSQL
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Busquem la càmera pel seu id
        cur.execute("""
            SELECT id, url, owner_id, latitude, longitude
            FROM camera
            WHERE id = %s
        """, (camera_id,))

        row = cur.fetchone()

        # Si no existeix cap càmera amb aquest id, retornem error 404
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        # Retornem la càmera trobada
        return {
            "id": row[0],
            "url": row[1],
            "owner_id": row[2],
            "latitude": float(row[3]),
            "longitude": float(row[4])
        }

    finally:
        # Tanquem cursor i connexió sempre
        cur.close()
        conn.close()
    
@app.put("/api/cameras/{camera_id}")
def update_camera(camera_id: int, camera: CameraUpdate):
    """
    Endpoint: PUT /api/cameras/{camera_id}

    Què fa:
    - Actualitza una càmera existent.
    - Comprova que la càmera existeixi.
    - Comprova que el nou owner_id existeixi.
    - Actualitza url, owner_id, latitude i longitude.

    Què rep:
    - camera_id a la URL
    - body JSON amb:
      {
          "url": "rtsp://192.168.1.80:554/stream",
          "owner_id": 2,
          "latitude": 41.24,
          "longitude": 1.73
      }

    Què retorna si va bé:
    {
        "message": "Càmera actualitzada correctament",
        "camera": {
            "id": 3,
            "url": "...",
            "owner_id": 2,
            "latitude": 41.24,
            "longitude": 1.73
        }
    }

    Què retorna si va malament:
    - 404 si la càmera no existeix
    - 400 si l'owner_id no existeix
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem que la càmera existeix
        cur.execute("""
            SELECT id
            FROM camera
            WHERE id = %s
        """, (camera_id,))
        camera_row = cur.fetchone()

        if camera_row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        # Comprovem que el nou owner existeix
        cur.execute("""
            SELECT id
            FROM users
            WHERE id = %s
        """, (camera.owner_id,))
        owner_row = cur.fetchone()

        if owner_row is None:
            raise HTTPException(
                status_code=400,
                detail="L'owner_id no existeix"
            )

        # Actualitzem la càmera
        cur.execute("""
            UPDATE camera
            SET url = %s,
                owner_id = %s,
                latitude = %s,
                longitude = %s
            WHERE id = %s
            RETURNING id, url, owner_id, latitude, longitude
        """, (
            camera.url,
            camera.owner_id,
            camera.latitude,
            camera.longitude,
            camera_id
        ))

        row = cur.fetchone()
        conn.commit()

        return {
            "message": "Càmera actualitzada correctament",
            "camera": {
                "id": row[0],
                "url": row[1],
                "owner_id": row[2],
                "latitude": float(row[3]),
                "longitude": float(row[4])
            }
        }

    finally:
        cur.close()
        conn.close()

@app.delete("/api/cameras/{camera_id}")
def delete_camera(camera_id: int):
    """
    Endpoint: DELETE /api/cameras/{camera_id}

    Què fa:
    - Elimina una càmera de la base de dades.
    - Comprova que la càmera existeixi abans d'eliminar-la.

    Què rep:
    - camera_id a la URL

    Exemple:
    DELETE /api/cameras/3

    Què retorna si va bé:
    {
        "message": "Càmera eliminada correctament"
    }

    Què retorna si va malament:
    - 404 si la càmera no existeix
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem si la càmera existeix
        cur.execute("""
            SELECT id
            FROM camera
            WHERE id = %s
        """, (camera_id,))
        row = cur.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        # Eliminem la càmera
        cur.execute("""
            DELETE FROM camera
            WHERE id = %s
        """, (camera_id,))
        conn.commit()

        return {
            "message": "Càmera eliminada correctament"
        }

    finally:
        cur.close()
        conn.close()
    
@app.get("/api/cameras/{camera_id}/stream")
def get_camera_stream(camera_id: int, request: Request):
    """
    Endpoint: GET /api/cameras/{camera_id}/stream

    Què fa:
    - Valida el token de sessió.
    - Obté l'usuari connectat.
    - Comprova que la càmera existeixi.
    - Comprova que la càmera estigui acceptada.
    - Comprova els permisos d'accés:
        * admin global
        * propietari de la càmera
        * privacitat public
        * privacitat community i pertinença a una comunitat
          associada a aquesta càmera
    - Genera un JWT temporal de lectura.
    - Retorna la URL HLS, el token i la data de caducitat.
    """

    # ------------------------------------------------------------
    # 1. Validar el token de sessió
    # ------------------------------------------------------------
    payload = verify_token(request)

    user_id = payload.get("user_id")
    role = payload.get("role")

    if user_id is None or role is None:
        raise HTTPException(
            status_code=401,
            detail="El token de sessió no conté la informació necessària"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        # ------------------------------------------------------------
        # 2. Obtenir la càmera, el propietari i la privacitat
        # ------------------------------------------------------------
        cur.execute("""
            SELECT
                c.id,
                c.owner_id,
                c.camera_status,
                u.privacity
            FROM camera c
            JOIN users u
              ON u.id = c.owner_id
            WHERE c.id = %s
        """, (camera_id,))

        camera_row = cur.fetchone()

        if camera_row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        db_camera_id = camera_row[0]
        owner_id = camera_row[1]
        camera_status_value = camera_row[2]
        privacity = camera_row[3]

        # ------------------------------------------------------------
        # 3. La càmera ha d'estar acceptada
        # ------------------------------------------------------------
        if camera_status_value != "accepted":
            raise HTTPException(
                status_code=403,
                detail="La càmera no està acceptada"
            )

        # ------------------------------------------------------------
        # 4. Comprovar permisos
        # ------------------------------------------------------------
        allowed = False

        # Admin global
        if role == "admin":
            allowed = True

        # Propietari de la càmera
        elif owner_id == user_id:
            allowed = True

        # Càmera pública
        elif privacity == "public":
            allowed = True

        # Accés per comunitat
        elif privacity == "community":
            cur.execute("""
                SELECT 1
                FROM camera_community cc
                JOIN community_member cm
                  ON cm.community_id = cc.community_id
                WHERE cc.camera_id = %s
                  AND cm.user_id = %s
                LIMIT 1
            """, (
                camera_id,
                user_id
            ))

            community_access = cur.fetchone()
            allowed = community_access is not None

        # Privacitat private
        elif privacity == "private":
            allowed = False

        else:
            raise HTTPException(
                status_code=500,
                detail="La privacitat de l'usuari no és vàlida"
            )

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="No tens permisos per veure aquest stream"
            )

        # ------------------------------------------------------------
        # 5. Registrar la visualitzacio (per a "cameres mes vistes")
        # Una fila per usuari+camera+dia; si ja hi ha una avui no en
        # duplica (el token es renova sol mentre es mira l'stream).
        # ------------------------------------------------------------
        cur.execute("""
            INSERT INTO display (user_id, camera_id, date)
            VALUES (%s, %s, CURRENT_DATE)
            ON CONFLICT (user_id, camera_id, date) DO NOTHING
        """, (user_id, db_camera_id))
        conn.commit()

        # ------------------------------------------------------------
        # 6. Generar token temporal de lectura
        # ------------------------------------------------------------
        token, expires_at = generate_stream_token(
            user_id=user_id,
            camera_id=db_camera_id,
            expires_minutes=5
        )

        # ------------------------------------------------------------
        # 6. Retornar URL HLS i token
        # ------------------------------------------------------------
        return {
            "camera_id": db_camera_id,
            "hls_url": f"{STREAM_BASE_URL}/cam{db_camera_id}/index.m3u8",
            "token": token,
            "expires": expires_at.isoformat()
        }

    finally:
        cur.close()
        conn.close()

def verify_token(request: Request):
    """
    Llegeix el token de sessió de l'header Authorization,
    el valida i retorna el payload.
    """

    authorization = request.headers.get("Authorization")

    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Falta la capçalera Authorization"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Format d'autorització incorrecte"
        )

    token = authorization.replace("Bearer ", "", 1)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="El token ha caducat"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="El token no és vàlid"
        )

@app.post("/api/mediamtx/auth")
def mediamtx_auth(data: MediaMTXAuthRequest):
    """
    Endpoint: POST /api/mediamtx/auth
    """

    # ------------------------------------------------------------
    # 1. Permetre publicar streams de prova
    # ------------------------------------------------------------
    if data.action == "publish":
        camera_id_raw = data.user
        publish_token = data.password
        requested_path = data.path or ""

        if not camera_id_raw or not publish_token:
            raise HTTPException(
                status_code=401,
                detail="Falten credencials de publicació"
            )

        try:
            camera_id = int(camera_id_raw)
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="camera_id de publicació no vàlid"
            )

        expected_path = f"cam{camera_id}"

        if requested_path != expected_path:
            raise HTTPException(
                status_code=403,
                detail="El path no correspon amb la càmera"
            )

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT id, publish_token, camera_status
                FROM camera
                WHERE id = %s
            """, (camera_id,))
            row = cur.fetchone()

            if row is None:
                raise HTTPException(
                    status_code=401,
                    detail="La càmera no existeix per publicar"
                )

            db_publish_token = row[1]

            if db_publish_token != publish_token:
                raise HTTPException(
                    status_code=401,
                    detail="Token de publicació incorrecte"
                )

            return {
                "status": "ok",
                "camera_id": camera_id
            }

        finally:
            cur.close()
            conn.close()

############DETECTIONS#########

def authenticate_camera(request: Request) -> int:
    """
    Valida les credencials de la càmera (capçaleres X-Camera-Id /
    X-Publish-Token) contra el publish_token guardat a la BBDD.
    Retorna l'id_camera si són correctes, o llença 401.
    """

    camera_id_raw = request.headers.get("X-Camera-Id")
    publish_token = request.headers.get("X-Publish-Token")

    if not camera_id_raw or not publish_token:
        raise HTTPException(
            status_code=401,
            detail="Falten les capçaleres X-Camera-Id / X-Publish-Token"
        )

    try:
        camera_id = int(camera_id_raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="X-Camera-Id no vàlid")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT publish_token
            FROM camera
            WHERE id = %s
        """, (camera_id,))
        row = cur.fetchone()

        if row is None or row[0] != publish_token:
            raise HTTPException(
                status_code=401,
                detail="Credencials de la càmera no vàlides"
            )
    finally:
        cur.close()
        conn.close()

    return camera_id


def _validate_upload_kind(file: UploadFile, expected_prefix: str, kind_label: str):
    """
    Comprova que el content_type del fitxer pujat comença pel prefix
    esperat ('image/' o 'video/'). No és una validació infal·lible (el
    content_type l'envia el client, es podria falsejar), però evita
    l'error més habitual: pujar un vídeo a un endpoint pensat per a
    imatges, o al revés.
    """
    content_type = file.content_type or ""
    if not content_type.startswith(expected_prefix):
        raise HTTPException(
            status_code=400,
            detail=f"S'esperava un fitxer de tipus {kind_label} (content-type rebut: '{content_type}')"
        )


@app.post("/api/detections_frame")
def create_detection_frame(
    request: Request,
    file: UploadFile = File(...),
    detected_at: str = Form(...),
    duration: int | None = Form(None),
    user_id: int | None = Form(None),
):
    """
    Endpoint: POST /api/detections_frame

    Què fa:
    - Rep la imatge (multipart) d'un frame des d'un dispositiu Edge,
      que ja ha passat pel Model 1 (YOLO) localment.
    - Valida les credencials de la càmera (capçaleres X-Camera-Id /
      X-Publish-Token), mateix mecanisme que /api/mediamtx/auth.
    - Puja la imatge a MinIO.
    - Desa la detecció amb status='fase2' (falta identificar l'espècie
      amb el Model 2/CNN) i type='frame_detection'.

    Què retorna si va bé:
    {
        "message": "Detecció de frame creada correctament",
        "detection": {
            ...
        }
    }
    """

    camera_id = authenticate_camera(request)
    _validate_upload_kind(file, "image/", "imatge")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Tipus de detecció: sempre 'frame_detection' per a aquest endpoint
        cur.execute("""
            SELECT id
            FROM detection_type
            WHERE type = 'frame_detection'
        """)
        type_row = cur.fetchone()

        if type_row is None:
            raise HTTPException(
                status_code=500,
                detail="El tipus de detecció 'frame_detection' no està configurat"
            )

        # Si hi ha user_id, comprovem que l'usuari existeix
        if user_id is not None:
            cur.execute("""
                SELECT id
                FROM users
                WHERE id = %s
            """, (user_id,))
            user_row = cur.fetchone()

            if user_row is None:
                raise HTTPException(
                    status_code=404,
                    detail="L'usuari no existeix"
                )

        # Pugem la imatge a MinIO
        extension = os.path.splitext(file.filename or "")[1] or ".jpg"
        object_name = f"detections/{camera_id}/{uuid.uuid4().hex}{extension}"
        url = upload_file(
            file.file,
            object_name,
            content_type=file.content_type or "image/jpeg",
        )

        # Inserim la detecció a la base de dades. status='fase2' perquè
        # el Model 1 (YOLO) ja s'ha executat a l'Edge — només falta
        # identificar l'espècie amb el Model 2 (CNN).
        cur.execute("""
            INSERT INTO detections (
                id_camera,
                detected_at,
                type,
                duration,
                status,
                url,
                user_id
            )
            VALUES (%s, %s, %s, %s, 'fase2', %s, %s)
            RETURNING id, id_camera, detected_at, type, duration, status, url, user_id
        """, (
            camera_id,
            detected_at,
            type_row[0],
            duration,
            url,
            user_id
        ))

        row = cur.fetchone()
        conn.commit()

        # Ja ha passat pel YOLO a l'Edge (status='fase2'): encolem
        # directament a fase 2 (CNN d'identificació d'espècie).
        queue_fase2.enqueue("jobs_phase2.process_phase2", row[0])

        return {
            "message": "Detecció de frame creada correctament",
            "detection": {
                "id": row[0],
                "id_camera": row[1],
                "detected_at": str(row[2]),
                "type": row[3],
                "duration": row[4],
                "status": row[5],
                "url": get_url(row[6]),
                "user_id": row[7]
            }
        }

    finally:
        cur.close()
        conn.close()

@app.post("/api/detections_video")
def create_detection_video(
    request: Request,
    file: UploadFile = File(...),
    detected_at: str = Form(...),
    duration: int | None = Form(None),
    user_id: int | None = Form(None),
    confidence: float | None = Form(None),
):
    """
    Endpoint: POST /api/detections_video

    Què fa:
    - Rep el vídeo (multipart) des d'un dispositiu Edge.
    - Valida les credencials de la càmera (capçaleres X-Camera-Id /
      X-Publish-Token), mateix mecanisme que /api/mediamtx/auth.
    - Puja el vídeo a MinIO.
    - Si l'Edge ja ha corregut el seu propi YOLO sobre el vídeo i envia
      una 'confidence' >= 0.5, ens saltem la fase 1 al Cloud (status
      queda directament a 'fase2'). Si no envia confidence, o és
      inferior a 0.5, cal córrer el Model 1 (YOLO) al Cloud (status
      queda a 'fase1').
    - Desa la detecció amb type='video_detection'.

    Què retorna si va bé:
    {
        "message": "Detecció de vídeo creada correctament",
        "detection": {
            ...
        }
    }
    """

    camera_id = authenticate_camera(request)
    _validate_upload_kind(file, "video/", "vídeo")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Tipus de detecció: sempre 'video_detection' per a aquest endpoint
        cur.execute("""
            SELECT id
            FROM detection_type
            WHERE type = 'video_detection'
        """)
        type_row = cur.fetchone()

        if type_row is None:
            raise HTTPException(
                status_code=500,
                detail="El tipus de detecció 'video_detection' no està configurat"
            )

        # Si hi ha user_id, comprovem que l'usuari existeix
        if user_id is not None:
            cur.execute("""
                SELECT id
                FROM users
                WHERE id = %s
            """, (user_id,))
            user_row = cur.fetchone()

            if user_row is None:
                raise HTTPException(
                    status_code=404,
                    detail="L'usuari no existeix"
                )

        # Decidim la fase segons la confidence del YOLO de l'Edge (si
        # n'ha corregut cap): prou alta -> ens saltem la fase 1.
        CONFIDENCE_THRESHOLD = 0.5

        if confidence is not None and confidence >= CONFIDENCE_THRESHOLD:
            initial_status = "fase2"
        else:
            initial_status = "fase1"

        # Pugem el vídeo a MinIO
        extension = os.path.splitext(file.filename or "")[1] or ".mp4"
        object_name = f"detections/{camera_id}/{uuid.uuid4().hex}{extension}"
        url = upload_file(
            file.file,
            object_name,
            content_type=file.content_type or "video/mp4",
        )

        # Inserim la detecció a la base de dades
        cur.execute("""
            INSERT INTO detections (
                id_camera,
                detected_at,
                type,
                duration,
                status,
                url,
                user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, id_camera, detected_at, type, duration, status, url, user_id
        """, (
            camera_id,
            detected_at,
            type_row[0],
            duration,
            initial_status,
            url,
            user_id
        ))

        row = cur.fetchone()
        conn.commit()

        # Encolem a la cua que toqui segons la fase inicial decidida abans.
        if initial_status == "fase1":
            queue_fase1.enqueue("jobs_phase1.process_frame_phase1", row[0])
        else:
            queue_fase2.enqueue("jobs_phase2.process_phase2", row[0])

        return {
            "message": "Detecció de vídeo creada correctament",
            "detection": {
                "id": row[0],
                "id_camera": row[1],
                "detected_at": str(row[2]),
                "type": row[3],
                "duration": row[4],
                "status": row[5],
                "url": get_url(row[6]),
                "user_id": row[7]
            }
        }

    finally:
        cur.close()
        conn.close()


@app.post("/api/user_upload_frame")
def user_upload_frame(request: Request, file: UploadFile = File(...)):
    """
    Endpoint: POST /api/user_upload_frame

    Què fa:
    - Requereix l'usuari autenticat (Bearer token).
    - Puja la imatge a MinIO.
    - Crea una detecció amb status='fase1' (encara no ha passat per cap
      dels dos models) i type='frame_detection'. No està associada a
      cap càmera (id_camera=NULL) — l'ha pujat un usuari directament.
    """

    user = get_current_user(request)
    _validate_upload_kind(file, "image/", "imatge")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id
            FROM detection_type
            WHERE type = 'frame_detection'
        """)
        type_row = cur.fetchone()

        if type_row is None:
            raise HTTPException(
                status_code=500,
                detail="El tipus de detecció 'frame_detection' no està configurat"
            )

        extension = os.path.splitext(file.filename or "")[1] or ".jpg"
        object_name = f"user_uploads/{user['user_id']}/{uuid.uuid4().hex}{extension}"
        url = upload_file(
            file.file,
            object_name,
            content_type=file.content_type or "image/jpeg",
        )

        cur.execute("""
            INSERT INTO detections (
                id_camera,
                detected_at,
                type,
                duration,
                status,
                url,
                user_id
            )
            VALUES (NULL, %s, %s, NULL, 'fase1', %s, %s)
            RETURNING id, id_camera, detected_at, type, duration, status, url, user_id
        """, (
            datetime.now(timezone.utc),
            type_row[0],
            url,
            user["user_id"]
        ))

        row = cur.fetchone()
        conn.commit()

        # Pujada directa d'un usuari: encara no ha passat per cap model,
        # comença sempre a fase 1 (YOLO).
        queue_fase1.enqueue("jobs_phase1.process_frame_phase1", row[0])

        return {
            "message": "Imatge pujada i detecció creada correctament",
            "detection": {
                "id": row[0],
                "id_camera": row[1],
                "detected_at": str(row[2]),
                "type": row[3],
                "duration": row[4],
                "status": row[5],
                "url": get_url(row[6]),
                "user_id": row[7]
            }
        }

    finally:
        cur.close()
        conn.close()


@app.post("/api/user_upload_video")
def user_upload_video(request: Request, file: UploadFile = File(...)):
    """
    Endpoint: POST /api/user_upload_video

    Anàleg a /api/user_upload_frame però per a vídeo
    (type='video_detection').
    """

    user = get_current_user(request)
    _validate_upload_kind(file, "video/", "vídeo")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id
            FROM detection_type
            WHERE type = 'video_detection'
        """)
        type_row = cur.fetchone()

        if type_row is None:
            raise HTTPException(
                status_code=500,
                detail="El tipus de detecció 'video_detection' no està configurat"
            )

        extension = os.path.splitext(file.filename or "")[1] or ".mp4"
        object_name = f"user_uploads/{user['user_id']}/{uuid.uuid4().hex}{extension}"
        url = upload_file(
            file.file,
            object_name,
            content_type=file.content_type or "video/mp4",
        )

        cur.execute("""
            INSERT INTO detections (
                id_camera,
                detected_at,
                type,
                duration,
                status,
                url,
                user_id
            )
            VALUES (NULL, %s, %s, NULL, 'fase1', %s, %s)
            RETURNING id, id_camera, detected_at, type, duration, status, url, user_id
        """, (
            datetime.now(timezone.utc),
            type_row[0],
            url,
            user["user_id"]
        ))

        row = cur.fetchone()
        conn.commit()

        # Pujada directa d'un usuari: comença sempre a fase 1 (YOLO).
        queue_fase1.enqueue("jobs_phase1.process_frame_phase1", row[0])

        return {
            "message": "Vídeo pujat i detecció creada correctament",
            "detection": {
                "id": row[0],
                "id_camera": row[1],
                "detected_at": str(row[2]),
                "type": row[3],
                "duration": row[4],
                "status": row[5],
                "url": get_url(row[6]),
                "user_id": row[7]
            }
        }

    finally:
        cur.close()
        conn.close()


###############################COMUNITATS#######################
@app.post("/api/communities")
def create_community(data: CommunityCreate, request: Request):
    """
    Endpoint: POST /api/communities

    Què fa:
    - Crea una nova comunitat.
    - Comprova que el nom no existeixi.
    - L'usuari autenticat que la crea es converteix automàticament en líder.
    - Afegeix automàticament el líder a community_member.

    Què rep:
    {
        "name": "Comunitat A"
    }

    Què retorna si va bé:
    {
        "message": "Comunitat creada correctament",
        "community": {
            "id": 1,
            "name": "Comunitat A",
            "leader_id": 3
        }
    }
    """

    user = get_current_user(request)
    leader_id = user["user_id"]

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem que no existeixi una comunitat amb aquest nom
        cur.execute("""
            SELECT id
            FROM community
            WHERE name = %s
        """, (data.name,))
        existing_community = cur.fetchone()

        if existing_community is not None:
            raise HTTPException(
                status_code=400,
                detail="Ja existeix una comunitat amb aquest nom"
            )

        # Creem la comunitat (el líder és sempre qui la crea)
        cur.execute("""
            INSERT INTO community (name, leader_id)
            VALUES (%s, %s)
            RETURNING id, name, leader_id
        """, (data.name, leader_id))

        row = cur.fetchone()
        community_id = row[0]

        # Afegim el líder com a membre de la comunitat
        cur.execute("""
            INSERT INTO community_member (community_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (community_id, leader_id))

        conn.commit()

        return {
            "message": "Comunitat creada correctament",
            "community": {
                "id": row[0],
                "name": row[1],
                "leader_id": row[2]
            }
        }

    finally:
        cur.close()
        conn.close()


@app.post("/api/communities/{community_id}/members")
def join_community(community_id: int, request: Request):
    """
    Endpoint: POST /api/communities/{community_id}/members

    Què fa:
    - L'usuari autenticat s'afegeix ell mateix com a membre de la comunitat
      (no es poden afegir altres usuaris — cadascú s'hi uneix pel seu compte).
    - Comprova que la comunitat existeixi.
    - Si ja n'és membre, no falla (idempotent).

    Què rep:
    community_id a la URL. Sense body: el membre és sempre qui fa la crida.

    Què retorna si va bé:
    {
        "message": "T'has unit a la comunitat correctament",
        "community_id": 1,
        "user_id": 7
    }
    """

    user = get_current_user(request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id
            FROM community
            WHERE id = %s
        """, (community_id,))
        community_row = cur.fetchone()

        if community_row is None:
            raise HTTPException(
                status_code=404,
                detail="La comunitat no existeix"
            )

        cur.execute("""
            INSERT INTO community_member (community_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (community_id, user["user_id"]))

        conn.commit()

        return {
            "message": "T'has unit a la comunitat correctament",
            "community_id": community_id,
            "user_id": user["user_id"]
        }

    finally:
        cur.close()
        conn.close()

@app.post("/api/communities/{community_id}/cameras")
def add_cameras_to_community(community_id: int, data: CommunityCamerasAdd, request: Request):
    """
    Endpoint: POST /api/communities/{community_id}/cameras

    Què fa:
    - Requereix que qui fa la crida sigui membre de la comunitat.
    - Afegeix diverses càmeres a una comunitat.
    - Comprova que la comunitat existeixi.
    - Comprova que cada càmera existeixi.
    - Insereix a camera_community.
    - Si una càmera ja hi és, no falla.

    Què rep:
    community_id a la URL

    Body:
    {
        "camera_ids": [1, 4, 6]
    }

    Què retorna si va bé:
    {
        "message": "Càmeres afegides correctament",
        "community_id": 1,
        "added_camera_ids": [1, 4, 6]
    }
    """

    require_community_member(community_id, request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem que la comunitat existeixi
        cur.execute("""
            SELECT id
            FROM community
            WHERE id = %s
        """, (community_id,))
        community_row = cur.fetchone()

        if community_row is None:
            raise HTTPException(
                status_code=404,
                detail="La comunitat no existeix"
            )

        # Comprovem que hi hagi càmeres
        if len(data.camera_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail="Has d'enviar almenys un camera_id"
            )

        # Comprovem i afegim cada càmera
        for camera_id in data.camera_ids:
            cur.execute("""
                SELECT id
                FROM camera
                WHERE id = %s
            """, (camera_id,))
            camera_row = cur.fetchone()

            if camera_row is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"La càmera amb id {camera_id} no existeix"
                )

            cur.execute("""
                INSERT INTO camera_community (camera_id, community_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (camera_id, community_id))

        conn.commit()

        return {
            "message": "Càmeres afegides correctament",
            "community_id": community_id,
            "added_camera_ids": data.camera_ids
        }

    finally:
        cur.close()
        conn.close()

@app.get("/api/communities")
def get_communities():
    """
    Retorna totes les comunitats amb la informació bàsica.
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT c.id, c.name, c.leader_id, u.mail
            FROM community c
            LEFT JOIN users u ON c.leader_id = u.id
            ORDER BY c.id
        """)

        rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "leader_id": row[2],
                "leader_mail": row[3]
            }
            for row in rows
        ]

    finally:
        cur.close()
        conn.close()


@app.get("/api/communities/{community_id}")
def get_community_detail(community_id: int):
    """
    Retorna el detall d'una comunitat:
    - dades bàsiques
    - líder
    - membres
    - càmeres
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comunitat
        cur.execute("""
            SELECT c.id, c.name, c.leader_id, u.mail
            FROM community c
            LEFT JOIN users u ON c.leader_id = u.id
            WHERE c.id = %s
        """, (community_id,))
        community_row = cur.fetchone()

        if community_row is None:
            raise HTTPException(
                status_code=404,
                detail="La comunitat no existeix"
            )

        # Membres
        cur.execute("""
            SELECT u.id, u.mail, u.role
            FROM community_member cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.community_id = %s
            ORDER BY u.id
        """, (community_id,))
        member_rows = cur.fetchall()

        # Càmeres
        cur.execute("""
            SELECT c.id, c.url, c.owner_id, c.latitude, c.longitude
            FROM camera_community cc
            JOIN camera c ON cc.camera_id = c.id
            WHERE cc.community_id = %s
            ORDER BY c.id
        """, (community_id,))
        camera_rows = cur.fetchall()

        return {
            "id": community_row[0],
            "name": community_row[1],
            "leader": {
                "id": community_row[2],
                "mail": community_row[3]
            } if community_row[2] is not None else None,
            "members": [
                {
                    "id": row[0],
                    "mail": row[1],
                    "role": row[2]
                }
                for row in member_rows
            ],
            "cameras": [
                {
                    "id": row[0],
                    "url": row[1],
                    "owner_id": row[2],
                    "latitude": row[3],
                    "longitude": row[4]
                }
                for row in camera_rows
            ]
        }

    finally:
        cur.close()
        conn.close()

@app.delete("/api/communities/{community_id}/members/{user_id}")
def remove_member_from_community(community_id: int, user_id: int, request: Request):
    require_community_leader(community_id, request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT leader_id
            FROM community
            WHERE id = %s
        """, (community_id,))
        row = cur.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="La comunitat no existeix")

        leader_id = row[0]

        if leader_id == user_id:
            raise HTTPException(
                status_code=400,
                detail="No pots eliminar el líder com a membre sense canviar abans el líder"
            )

        cur.execute("""
            DELETE FROM community_member
            WHERE community_id = %s AND user_id = %s
        """, (community_id, user_id))

        conn.commit()

        return {
            "message": "Membre eliminat correctament",
            "community_id": community_id,
            "user_id": user_id
        }

    finally:
        cur.close()
        conn.close()

@app.delete("/api/communities/{community_id}/cameras/{camera_id}")
def remove_camera_from_community(community_id: int, camera_id: int, request: Request):
    require_community_leader(community_id, request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM camera_community
            WHERE community_id = %s AND camera_id = %s
        """, (community_id, camera_id))

        conn.commit()

        return {
            "message": "Càmera eliminada correctament de la comunitat",
            "community_id": community_id,
            "camera_id": camera_id
        }

    finally:
        cur.close()
        conn.close()

@app.delete("/api/communities/{community_id}")
def delete_community(community_id: int, request: Request):
    require_community_leader(community_id, request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM community WHERE id = %s", (community_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="La comunitat no existeix")

        cur.execute("""
            DELETE FROM community
            WHERE id = %s
        """, (community_id,))

        conn.commit()

        return {
            "message": "Comunitat eliminada correctament",
            "community_id": community_id
        }

    finally:
        cur.close()
        conn.close()

@app.put("/api/communities/{community_id}/leader")
def update_community_leader(community_id: int, data: CommunityLeaderUpdate, request: Request):
    """
    Canvia el líder d'una comunitat. Només el líder actual ho pot fer.
    """

    require_community_leader(community_id, request)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comunitat existeix
        cur.execute("SELECT id FROM community WHERE id = %s", (community_id,))
        community_row = cur.fetchone()

        if community_row is None:
            raise HTTPException(status_code=404, detail="La comunitat no existeix")

        # Usuari existeix
        cur.execute("SELECT id, mail FROM users WHERE id = %s", (data.leader_id,))
        user_row = cur.fetchone()

        if user_row is None:
            raise HTTPException(status_code=404, detail="L'usuari no existeix")

        # Actualitzar líder
        cur.execute("""
            UPDATE community
            SET leader_id = %s
            WHERE id = %s
        """, (data.leader_id, community_id))

        # Afegir també com a membre
        cur.execute("""
            INSERT INTO community_member (community_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (community_id, data.leader_id))

        conn.commit()

        return {
            "message": "Líder actualitzat correctament",
            "community_id": community_id,
            "leader": {
                "id": user_row[0],
                "mail": user_row[1]
            }
        }

    finally:
        cur.close()
        conn.close()

###############################BUSCADORS#######################

@app.get("/api/users/search")
def search_users_by_email(email: str = Query(...)):
    """
    Endpoint: GET /api/users/search?email=...
    Retorna usuaris que contenen aquest text al mail.
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, mail, role
            FROM users
            WHERE mail ILIKE %s
            ORDER BY mail
            LIMIT 20
        """, (f"%{email}%",))

        rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "mail": row[1],
                "role": row[2]
            }
            for row in rows
        ]

    finally:
        cur.close()
        conn.close()