import psycopg
from .config import settings

def connect():
    return psycopg.connect(settings.database_url, connect_timeout=5)

def get_state(key: str):
    with connect() as c:
        row = c.execute("SELECT value FROM load_state WHERE key=%s", (key,)).fetchone()
    return row[0] if row else None

def set_state(key: str, value: str):
    with connect() as c:
        c.execute(
            "INSERT INTO load_state(key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, value))

def counts() -> dict:
    with connect() as c:
        cur, total, groups = c.execute(
            "SELECT count(*) FILTER (WHERE is_current), count(*), "
            "count(DISTINCT group_id) FILTER (WHERE is_current) FROM company_versions").fetchone()
    return {"companies": cur, "versions": total, "groups": groups}
