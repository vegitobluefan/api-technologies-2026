"""Enrichment Service (владелец: Артём).
Ждёт окончания первичной загрузки Loader и поддерживает актуальный срез."""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .wait import wait_for_initial_load

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("enrichment")


def run():
    wait_for_initial_load()
    log.info("первичная загрузка закончена, начинаем обогащение")
    # TODO по критериям:
    # 1) isBankClient: POST /abs/v1/legal-clients:lookup пачками до 500 ИНН, заголовки config.abs_headers()
    #    -> таблица bank_clients
    # 2) собрать company_snapshot: текущие company_versions + company_groups + bank_clients,
    #    data_as_of = время сборки
    # 3) прогреть Redis: ключ company:{inn} = platform_common.mapping.to_company_info(row), TTL = CACHE_TTL_SECONDS
    # 4) повторять после каждого инкремента (следить за load_state.last_sync_at)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=run, daemon=True, name="enrichment").start()
    yield


app = FastAPI(title="enrichment", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
