"""
Aplica les migracions pendents de migrations/*.sql, en ordre, contra
DATABASE_URL. Es pot cridar en cada arrencada del backend: si no hi ha
res nou, només fa una consulta i acaba de seguida.

Cada migració s'aplica com a molt una vegada per BBDD (es registra a
schema_migrations). Si una falla, es fa rollback, NO es marca com
aplicada, i el script surt amb error — perquè el contenidor no arrenqui
uvicorn contra un esquema a mitges.
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_applied_migrations(cur) -> set[str]:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename text PRIMARY KEY,
            applied_at timestamp without time zone DEFAULT now() NOT NULL
        )
    """)
    cur.execute("SELECT filename FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def main():
    if not MIGRATIONS_DIR.exists():
        print("[migrations] No hi ha carpeta de migracions, no cal fer res.")
        return

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migration_files:
        print("[migrations] No hi ha cap fitxer de migració.")
        return

    conn = psycopg.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            applied = get_applied_migrations(cur)
        conn.commit()

        pending = [f for f in migration_files if f.name not in applied]

        if not pending:
            print(f"[migrations] Esquema al dia ({len(applied)} migracions aplicades).")
            return

        for migration_file in pending:
            print(f"[migrations] Aplicant {migration_file.name}...")
            sql = migration_file.read_text()

            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (migration_file.name,)
                    )
                conn.commit()
                print(f"[migrations] OK: {migration_file.name}")
            except Exception as exc:
                conn.rollback()
                print(f"[migrations] ERROR aplicant {migration_file.name}: {exc}")
                sys.exit(1)

        print(f"[migrations] Fet. {len(pending)} migracions noves aplicades.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
