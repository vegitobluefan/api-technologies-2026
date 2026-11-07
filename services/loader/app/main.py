import logging, threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import db
from .config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("loader")
_stop = threading.Event()

def run_forever():
    """Authenticate -> первичная загрузка (если не было) -> инкремент по расписанию.
    Любая ошибка (мок/БД недоступны) = пауза с backoff и новая попытка, процесс не падает."""
    from .incremental import incremental_load
    from .loader import initial_load
    from .soap_client import SparkClient

    delay = 2
    while not _stop.is_set():
        try:
            client = SparkClient()
            client.authenticate()
            delay = 2
            if db.get_state("initial_done") != "true":
                initial_load(client)
            while not _stop.is_set():
                incremental_load(client)
                _stop.wait(settings.incremental_interval_sec)
        except Exception:
            log.exception("цикл загрузки упал, повтор через %s с", delay)
            _stop.wait(delay)
            delay = min(delay * 2, 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=run_forever, daemon=True, name="loader")
    t.start()
    yield
    _stop.set()

app = FastAPI(title="loader", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/status")
def status():
    """Для demo.sh и README: сколько загружено и закончена ли первичная загрузка."""
    try:
        return {"initial_done": db.get_state("initial_done") == "true",
                "initial_loaded_at": db.get_state("initial_loaded_at"),
                "last_sync_at": db.get_state("last_sync_at"),
                **db.counts()}
    except Exception as e:
        return {"initial_done": False, "error": str(e)}
