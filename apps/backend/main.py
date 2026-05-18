from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from urllib.parse import parse_qs

import psycopg
import os
import jwt

import secrets


app = FastAPI()

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
STREAM_BASE_URL = os.getenv("STREAM_BASE_URL", "wss://media.plataforma.org/live")

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

class DetectionCreate(BaseModel):
    # Id de la càmera que ha generat la detecció
    id_camera: int

    # Data i hora de la detecció
    detected_at: str

    # Id del tipus de detecció
    type: int

    # Durada associada a la detecció, si escau
    duration: int | None = None

    # Estat de la detecció
    status: str

    # Ruta o URL de la imatge/crop associat
    url: str | None = None

    # Usuari associat a la detecció, si n'hi ha
    user_id: int | None = None

class DetectionStatusUpdate(BaseModel):
    # Nou estat de la detecció
    status: str

class CommunityCreate(BaseModel):
    # Nombre de la comunitat
    name: str

    # Usuari que serà el líder de la comunitat
    leader_id: int

class CommunityMembersAdd(BaseModel):
    # Llista d'usuaris a afegir a la comunitat
    user_ids: list[int]

class CommunityCamerasAdd(BaseModel):
    # Llista de càmeres a associar a la comunitat
    camera_ids: list[int]

class CommunityLeaderUpdate(BaseModel):
    leader_id: int

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




    ##############camara##############

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
    - Valida el token de sessió de l'usuari
    - Comprova que la càmera existeixi
    - Comprova si l'usuari té permís per veure aquesta càmera
    - Genera un token temporal per al stream
    - Retorna la URL HLS del Media Server i el token temporal
    """

    payload = verify_token(request)

    user_id = payload["user_id"]
    role = payload["role"]

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem que la càmera existeix
        cur.execute("""
            SELECT id, owner_id
            FROM camera
            WHERE id = %s
        """, (camera_id,))
        camera_row = cur.fetchone()

        if camera_row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        owner_id = camera_row[1]

        # 1. Admin global
        if role == "admin":
            allowed = True

        # 2. Owner de la càmera
        elif owner_id == user_id:
            allowed = True

        # 3. Privacitat del propietari
        else:
            cur.execute("""
                SELECT u.privacity
                FROM users u
                JOIN camera c ON c.owner_id = u.id
                WHERE c.id = %s
            """, (camera_id,))
            privacy_row = cur.fetchone()

            if privacy_row is None:
                raise HTTPException(
                    status_code=404,
                    detail="No s'ha pogut determinar la privacitat"
                )

            privacity = privacy_row[0]

            if privacity == "public":
                allowed = True

            elif privacity == "community":
                cur.execute("""
                    SELECT 1
                    FROM community_member cm1
                    JOIN community_member cm2
                      ON cm1.community_id = cm2.community_id
                    WHERE cm1.user_id = %s
                      AND cm2.user_id = %s
                    LIMIT 1
                """, (user_id, owner_id))
                same_community = cur.fetchone()
                allowed = same_community is not None

            else:
                # private
                allowed = False

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="No tens permisos per veure aquest stream"
            )

        # Generem token temporal del stream
        token, expires_at = generate_stream_token(
            user_id=user_id,
            camera_id=camera_id,
            expires_minutes=5
        )

        return {
            "hls_url": f"http://localhost:8888/cam{camera_id}/index.m3u8",
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
                SELECT id, publish_token
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


    # ------------------------------------------------------------
    # 2. Per llegir streams, exigim token
    # ------------------------------------------------------------
    if data.action not in ["read", "playback"]:
        raise HTTPException(
            status_code=403,
            detail="Acció no permesa"
        )

    raw_token = None

    if data.token:
        raw_token = data.token
    elif data.password:
        raw_token = data.password
    elif data.query:
        parsed_query = parse_qs(data.query)
        if "jwt" in parsed_query and len(parsed_query["jwt"]) > 0:
            raw_token = parsed_query["jwt"][0]
        elif "token" in parsed_query and len(parsed_query["token"]) > 0:
            raw_token = parsed_query["token"][0]

    if raw_token is None:
        raise HTTPException(
            status_code=401,
            detail="Falta el token"
        )

    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=["HS256"])
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

    token_camera_id = payload.get("camera_id")
    token_user_id = payload.get("user_id")

    if token_camera_id is None or token_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="El token no conté la informació necessària"
        )

    requested_path = data.path or ""
    requested_camera_id = requested_path.replace("cam", "")

    if str(token_camera_id) != str(requested_camera_id):
        raise HTTPException(
            status_code=403,
            detail="Aquest token no té permís per accedir a aquest stream"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id
            FROM users
            WHERE id = %s
        """, (token_user_id,))
        user_row = cur.fetchone()

        if user_row is None:
            raise HTTPException(
                status_code=401,
                detail="L'usuari del token no existeix"
            )

        cur.execute("""
            SELECT id
            FROM camera
            WHERE id = %s
        """, (token_camera_id,))
        camera_row = cur.fetchone()

        if camera_row is None:
            raise HTTPException(
                status_code=401,
                detail="La càmera del token no existeix"
            )

        return {"status": "ok"}

    finally:
        cur.close()
        conn.close()

############DETECTIONS#########

@app.post("/api/detections/frame")
def create_detection_frame(detection: DetectionCreate):
    """
    Endpoint: POST /api/detections/frame

    Què fa:
    - Rep una detecció basada en un frame procedent d'un dispositiu Edge.
    - Comprova que la càmera existeixi.
    - Comprova que el tipus de detecció existeixi.
    - Si es proporciona user_id, comprova que l'usuari existeixi.
    - Desa la detecció a la taula detections.

    Què rep:
    {
        "id_camera": 1,
        "detected_at": "2026-04-20T10:30:00",
        "type": 1,
        "duration": null,
        "status": "waiting",
        "url": "/detections/frame_001.jpg",
        "user_id": 1
    }

    Què retorna si va bé:
    {
        "message": "Detecció de frame creada correctament",
        "detection": {
            ...
        }
    }
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem que la càmera existeix
        cur.execute("""
            SELECT id
            FROM camera
            WHERE id = %s
        """, (detection.id_camera,))
        camera_row = cur.fetchone()

        if camera_row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        # Comprovem que el tipus de detecció existeix
        cur.execute("""
            SELECT id
            FROM detection_type
            WHERE id = %s
        """, (detection.type,))
        type_row = cur.fetchone()

        if type_row is None:
            raise HTTPException(
                status_code=404,
                detail="El tipus de detecció no existeix"
            )

        # Si hi ha user_id, comprovem que l'usuari existeix
        if detection.user_id is not None:
            cur.execute("""
                SELECT id
                FROM users
                WHERE id = %s
            """, (detection.user_id,))
            user_row = cur.fetchone()

            if user_row is None:
                raise HTTPException(
                    status_code=404,
                    detail="L'usuari no existeix"
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
            detection.id_camera,
            detection.detected_at,
            detection.type,
            detection.duration,
            detection.status,
            detection.url,
            detection.user_id
        ))

        row = cur.fetchone()
        conn.commit()

        return {
            "message": "Detecció de frame creada correctament",
            "detection": {
                "id": row[0],
                "id_camera": row[1],
                "detected_at": str(row[2]),
                "type": row[3],
                "duration": row[4],
                "status": row[5],
                "url": row[6],
                "user_id": row[7]
            }
        }

    finally:
        cur.close()
        conn.close()

@app.post("/api/detections/video")
def create_detection_video(detection: DetectionCreate):
    """
    Endpoint: POST /api/detections/video

    Què fa:
    - Rep una detecció basada en vídeo.
    - Comprova que la càmera existeixi.
    - Comprova que el tipus de detecció existeixi.
    - Si es proporciona user_id, comprova que l'usuari existeixi.
    - Desa la detecció a la taula detections.

    Què rep:
    {
        "id_camera": 1,
        "detected_at": "2026-04-20T10:45:00",
        "type": 2,
        "duration": 8,
        "status": "waiting",
        "url": "/detections/video_clip_003.mp4",
        "user_id": 1
    }

    Què retorna si va bé:
    {
        "message": "Detecció de vídeo creada correctament",
        "detection": {
            ...
        }
    }
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem que la càmera existeix
        cur.execute("""
            SELECT id
            FROM camera
            WHERE id = %s
        """, (detection.id_camera,))
        camera_row = cur.fetchone()

        if camera_row is None:
            raise HTTPException(
                status_code=404,
                detail="La càmera no existeix"
            )

        # Comprovem que el tipus de detecció existeix
        cur.execute("""
            SELECT id
            FROM detection_type
            WHERE id = %s
        """, (detection.type,))
        type_row = cur.fetchone()

        if type_row is None:
            raise HTTPException(
                status_code=404,
                detail="El tipus de detecció no existeix"
            )

        # Si hi ha user_id, comprovem que l'usuari existeix
        if detection.user_id is not None:
            cur.execute("""
                SELECT id
                FROM users
                WHERE id = %s
            """, (detection.user_id,))
            user_row = cur.fetchone()

            if user_row is None:
                raise HTTPException(
                    status_code=404,
                    detail="L'usuari no existeix"
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
            detection.id_camera,
            detection.detected_at,
            detection.type,
            detection.duration,
            detection.status,
            detection.url,
            detection.user_id
        ))

        row = cur.fetchone()
        conn.commit()

        return {
            "message": "Detecció de vídeo creada correctament",
            "detection": {
                "id": row[0],
                "id_camera": row[1],
                "detected_at": str(row[2]),
                "type": row[3],
                "duration": row[4],
                "status": row[5],
                "url": row[6],
                "user_id": row[7]
            }
        }

    finally:
        cur.close()
        conn.close()

@app.post("/api/detections/next-to-validate")
def get_next_detection_to_validate():
    """
    Endpoint: POST /api/detections/next-to-validate

    Què fa:
    - Busca la primera detecció amb estat 'waiting'
    - La selecciona en ordre d'entrada a la base de dades (id ascendent)
    - Canvia el seu estat a 'in_process'
    - La retorna perquè pugui ser validada

    Què rep:
    - No rep body

    Què retorna si hi ha una detecció pendent:
    {
        "message": "Detecció enviada a validació",
        "detection": {
            "id": 3,
            "id_camera": 1,
            "detected_at": "2026-04-20 12:00:00",
            "type": 1,
            "duration": null,
            "status": "in_process",
            "url": "/detections/frame_001.jpg",
            "user_id": 1
        }
    }

    Què retorna si no hi ha deteccions pendents:
    {
        "message": "No hi ha deteccions pendents de validar"
    }
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Busquem la detecció més antiga pendent de validar
        cur.execute("""
            SELECT id
            FROM detections
            WHERE status = 'waiting'
            ORDER BY id ASC
            LIMIT 1
        """)
        row = cur.fetchone()

        # Si no n'hi ha cap, retornem un missatge informatiu
        if row is None:
            return {
                "message": "No hi ha deteccions pendents de validar"
            }

        detection_id = row[0]

        # Actualitzem l'estat a 'in_process' i retornem la detecció actualitzada
        cur.execute("""
            UPDATE detections
            SET status = 'in_process'
            WHERE id = %s
            RETURNING id, id_camera, detected_at, type, duration, status, url, user_id
        """, (detection_id,))

        updated_row = cur.fetchone()
        conn.commit()

        return {
            "message": "Detecció enviada a validació",
            "detection": {
                "id": updated_row[0],
                "id_camera": updated_row[1],
                "detected_at": str(updated_row[2]),
                "type": updated_row[3],
                "duration": updated_row[4],
                "status": updated_row[5],
                "url": updated_row[6],
                "user_id": updated_row[7]
            }
        }

    finally:
        cur.close()
        conn.close()

@app.post("/api/detections/{detection_id}/send-to-validate")
def send_detection_to_validate(detection_id: int):
    """
    Endpoint: POST /api/detections/{detection_id}/send-to-validate

    Què fa:
    - Busca una detecció concreta pel seu id
    - Comprova que existeixi
    - Comprova que estigui en estat 'waiting'
    - La canvia a 'in_process'
    - La retorna per tal que pugui ser validada

    Què rep:
    - detection_id a la URL

    Exemple:
    POST /api/detections/5/send-to-validate

    Què retorna si va bé:
    {
        "message": "Detecció enviada a validació",
        "detection": {
            "id": 5,
            "id_camera": 1,
            "detected_at": "2026-04-20 12:00:00",
            "type": 1,
            "duration": null,
            "status": "in_process",
            "url": "/detections/frame_001.jpg",
            "user_id": 1
        }
    }

    Què retorna si va malament:
    - 404 si la detecció no existeix
    - 400 si la detecció no està en estat 'waiting'
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Busquem la detecció pel seu id
        cur.execute("""
            SELECT id, id_camera, detected_at, type, duration, status, url, user_id
            FROM detections
            WHERE id = %s
        """, (detection_id,))
        row = cur.fetchone()

        # Si no existeix, retornem error 404
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="La detecció no existeix"
            )

        # Comprovem que l'estat actual sigui 'waiting'
        current_status = row[5]

        if current_status != "waiting":
            raise HTTPException(
                status_code=400,
                detail="La detecció no està en estat waiting"
            )

        # Actualitzem la detecció a 'in_process'
        cur.execute("""
            UPDATE detections
            SET status = 'in_process'
            WHERE id = %s
            RETURNING id, id_camera, detected_at, type, duration, status, url, user_id
        """, (detection_id,))
        updated_row = cur.fetchone()

        conn.commit()

        return {
            "message": "Detecció enviada a validació",
            "detection": {
                "id": updated_row[0],
                "id_camera": updated_row[1],
                "detected_at": str(updated_row[2]),
                "type": updated_row[3],
                "duration": updated_row[4],
                "status": updated_row[5],
                "url": updated_row[6],
                "user_id": updated_row[7]
            }
        }

    finally:
        cur.close()
        conn.close()

@app.put("/api/detections/{detection_id}/status")
def update_detection_status(detection_id: int, data: DetectionStatusUpdate):
    """
    Endpoint: PUT /api/detections/{detection_id}/status

    Què fa:
    - Busca una detecció pel seu id
    - Comprova que existeixi
    - Comprova que el nou estat sigui un dels 4 permesos
    - Actualitza l'estat de la detecció
    - Retorna la detecció actualitzada

    Estats permesos:
    - waiting
    - in_process
    - validated
    - not_validated

    Què rep:
    - detection_id a la URL
    - body JSON:
      {
          "status": "validated"
      }

    Què retorna si va bé:
    {
        "message": "Estat de la detecció actualitzat correctament",
        "detection": {
            "id": 5,
            "id_camera": 1,
            "detected_at": "2026-04-20 12:00:00",
            "type": 1,
            "duration": null,
            "status": "validated",
            "url": "/detections/frame_001.jpg",
            "user_id": 1
        }
    }

    Què retorna si va malament:
    - 404 si la detecció no existeix
    - 400 si l'estat no és vàlid
    """

    # Llista d'estats permesos
    allowed_statuses = ["waiting", "in_process", "validated", "not_validated"]

    # Comprovem que l'estat rebut sigui vàlid
    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="L'estat no és vàlid"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comprovem que la detecció existeix
        cur.execute("""
            SELECT id
            FROM detections
            WHERE id = %s
        """, (detection_id,))
        row = cur.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="La detecció no existeix"
            )

        # Actualitzem l'estat de la detecció
        cur.execute("""
            UPDATE detections
            SET status = %s
            WHERE id = %s
            RETURNING id, id_camera, detected_at, type, duration, status, url, user_id
        """, (data.status, detection_id))

        updated_row = cur.fetchone()
        conn.commit()

        return {
            "message": "Estat de la detecció actualitzat correctament",
            "detection": {
                "id": updated_row[0],
                "id_camera": updated_row[1],
                "detected_at": str(updated_row[2]),
                "type": updated_row[3],
                "duration": updated_row[4],
                "status": updated_row[5],
                "url": updated_row[6],
                "user_id": updated_row[7]
            }
        }

    finally:
        cur.close()
        conn.close()



###############################COMUNITATS#######################
@app.post("/api/communities")
def create_community(data: CommunityCreate):
    """
    Endpoint: POST /api/communities

    Què fa:
    - Crea una nova comunitat.
    - Comprova que el nom no existeixi.
    - Comprova que el líder existeixi.
    - Desa la comunitat amb el seu líder.
    - Afegeix automàticament el líder a community_member.

    Què rep:
    {
        "name": "Comunitat A",
        "leader_id": 3
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

        # Comprovem que el líder existeixi
        cur.execute("""
            SELECT id
            FROM users
            WHERE id = %s
        """, (data.leader_id,))
        leader_row = cur.fetchone()

        if leader_row is None:
            raise HTTPException(
                status_code=404,
                detail="El líder no existeix"
            )

        # Creem la comunitat
        cur.execute("""
            INSERT INTO community (name, leader_id)
            VALUES (%s, %s)
            RETURNING id, name, leader_id
        """, (data.name, data.leader_id))

        row = cur.fetchone()
        community_id = row[0]

        # Afegim el líder com a membre de la comunitat
        cur.execute("""
            INSERT INTO community_member (community_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (community_id, data.leader_id))

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
def add_members_to_community(community_id: int, data: CommunityMembersAdd):
    """
    Endpoint: POST /api/communities/{community_id}/members

    Què fa:
    - Afegeix diversos usuaris a una comunitat.
    - Comprova que la comunitat existeixi.
    - Comprova que cada usuari existeixi.
    - Insereix a community_member.
    - Si un usuari ja hi és, no falla.

    Què rep:
    community_id a la URL

    Body:
    {
        "user_ids": [2, 5, 8]
    }

    Què retorna si va bé:
    {
        "message": "Membres afegits correctament",
        "community_id": 1,
        "added_user_ids": [2, 5, 8]
    }
    """

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

        # Comprovem que hi hagi usuaris
        if len(data.user_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail="Has d'enviar almenys un user_id"
            )

        # Comprovem i afegim cada usuari
        for user_id in data.user_ids:
            cur.execute("""
                SELECT id
                FROM users
                WHERE id = %s
            """, (user_id,))
            user_row = cur.fetchone()

            if user_row is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"L'usuari amb id {user_id} no existeix"
                )

            cur.execute("""
                INSERT INTO community_member (community_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (community_id, user_id))

        conn.commit()

        return {
            "message": "Membres afegits correctament",
            "community_id": community_id,
            "added_user_ids": data.user_ids
        }

    finally:
        cur.close()
        conn.close()

@app.post("/api/communities/{community_id}/cameras")
def add_cameras_to_community(community_id: int, data: CommunityCamerasAdd):
    """
    Endpoint: POST /api/communities/{community_id}/cameras

    Què fa:
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
def remove_member_from_community(community_id: int, user_id: int):
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
def remove_camera_from_community(community_id: int, camera_id: int):
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
def delete_community(community_id: int):
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
def update_community_leader(community_id: int, data: CommunityLeaderUpdate):
    """
    Canvia el líder d'una comunitat.
    """

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