import logging, time
import psycopg
from .config import settings

log = logging.getLogger("enrichment")

def wait_for_initial_load(poll: float = 5.0):
    """Блокирует, пока Loader не выставит load_state.initial_done='true'."""
    while True:
        try:
            with psycopg.connect(settings.database_url, connect_timeout=5) as c:
                row = c.execute("SELECT value FROM load_state WHERE key='initial_done'").fetchone()
            if row and row[0] == "true":
                return
        except Exception as e:
            log.warning("ждём БД/Loader: %s", e)
        time.sleep(poll)
