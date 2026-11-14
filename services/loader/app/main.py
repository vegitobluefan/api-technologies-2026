import json
import logging
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import settings
from .store import make_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("loader")
_stop = threading.Event()

store = make_store(settings.loader_dry_run)
VALID_FROM_ACTUAL = settings.scd2_valid_from.strip().lower() != "load"   # по умолчанию valid_from = ActualDate
state = {"client": None, "last_error": None}   # общий SparkClient для фонового цикла и POST /sync


def run_forever():
    """Authenticate -> первичная загрузка (если не было) -> инкремент по расписанию.
    Любая ошибка (мок/БД недоступны) = пауза с backoff и новая попытка, процесс не падает."""
    from .incremental import incremental_load
    from .loader import initial_load
    from .soap_client import AuthFailed, SparkClient

    delay = 2
    while not _stop.is_set():
        try:
            client = SparkClient()
            client.authenticate()
            state["client"] = client
            delay = 2
            if store.get_state("initial_done") != "true":
                initial_load(client, store, settings.loader_workers, VALID_FROM_ACTUAL)
            while not _stop.is_set():
                incremental_load(client, store, settings.loader_workers, VALID_FROM_ACTUAL)
                state["last_error"] = None
                _stop.wait(settings.incremental_interval_sec)
        except AuthFailed as e:
            # "громко": CRITICAL в лог и текст ошибки в /status. Ждём дольше, логин сам не исправится.
            state["last_error"] = str(e)
            log.critical("!!! %s. Исправь .env и перезапусти loader !!!", e)
            _stop.wait(60)
        except Exception as e:
            state["last_error"] = f"{type(e).__name__}: {e}"
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
    from .loader import progress
    try:
        initial_versions = store.get_state("initial_versions")
        duration = store.get_state("initial_duration_sec")
        skipped = store.get_state("initial_skipped")
        return {"initial_done": store.get_state("initial_done") == "true",
                "initial_loaded_at": store.get_state("initial_loaded_at"),
                "initial_duration_sec": float(duration) if duration else None,
                "initial_versions": int(initial_versions) if initial_versions else None,
                "initial_skipped": int(skipped) if skipped else None,
                "last_sync_at": store.get_state("last_sync_at"),
                "changed_inns": json.loads(store.get_state("changed_inns") or "[]"),
                "progress": progress,
                "last_error": state["last_error"],
                "dry_run": settings.loader_dry_run,
                **store.counts()}
    except Exception as e:
        return {"initial_done": False, "error": str(e)}


def _error(status: int, code: str, message: str):
    """Ошибка в общем формате платформы: code, message, traceId."""
    rid = str(uuid.uuid4())
    return JSONResponse(status_code=status, headers={"X-Request-Id": rid},
                        content={"code": code, "message": message, "traceId": rid})


@app.post("/sync")
def sync():
    """Запустить инкремент сейчас, не дожидаясь расписания. Возвращает число новых версий SCD2."""
    from .incremental import incremental_load
    if store.get_state("initial_done") != "true" or state["client"] is None:
        return _error(409, "INVALID_REQUEST", "Первичная загрузка ещё не закончена")
    try:
        result = incremental_load(state["client"], store, settings.loader_workers, VALID_FROM_ACTUAL)
    except Exception as e:
        log.exception("POST /sync упал")
        return _error(503, "SERVICE_UNAVAILABLE", f"Инкремент не выполнен: {e}")
    return {**result, **store.counts()}
