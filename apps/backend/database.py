import os
import re
from dotenv import load_dotenv
import psycopg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Els workers (worker-phase1/worker-phase2) NO fan servir network_mode: host
# com el backend, així que "localhost" de dins seu no arriba al teu Postgres
# natiu. En lloc de repetir usuari/contrasenya a un altre lloc (i trencar-ho
# per a qui cloni el repo amb credencials diferents), el docker-compose.yml
# només els passa DB_HOST_OVERRIDE=host.docker.internal, i aquí substituïm
# només l'amfitrió, mantenint les credencials que ja hi ha a DATABASE_URL.
DB_HOST_OVERRIDE = os.getenv("DB_HOST_OVERRIDE")
if DB_HOST_OVERRIDE and DATABASE_URL:
    DATABASE_URL = re.sub(r"@[^:/@]+:", f"@{DB_HOST_OVERRIDE}:", DATABASE_URL, count=1)

def get_connection():
    return psycopg.connect(DATABASE_URL)