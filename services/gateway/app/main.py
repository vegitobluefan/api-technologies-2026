"""API Gateway (владелец: Савелий). Контракт: contracts/api-gateway/openapi.yaml.
Проверяет Bearer, валидирует ИНН, пробрасывает X-Request-Id и сводит ошибки нижних сервисов к единому формату."""
import secrets
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Path, Query, Request

from platform_common.errors import INN_PATTERN, ApiError, install
from platform_common.upstream import get_json

from .config import settings

Inn = Annotated[str, Path(pattern=INN_PATTERN, description="ИНН юрлица, 10 цифр")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient()
    yield
    await app.state.client.aclose()


app = FastAPI(title="API Gateway", lifespan=lifespan)
install(app)


def require_token(request: Request):
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else ""
    if not token or not secrets.compare_digest(token, settings.gateway_token):
        raise ApiError(401, "UNAUTHORIZED", "Нужен корректный Bearer-токен")


async def _proxy(request: Request, url: str, params: dict | None = None):
    return await get_json(request.app.state.client, url, request.state.request_id,
                          params=params, timeout=settings.upstream_timeout_sec)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/companies/{inn}", dependencies=[Depends(require_token)])
async def company_info(request: Request, inn: Inn):
    return await _proxy(request, f"{settings.client_info_url}/v1/companies/{inn}")


@app.get("/v1/companies/{inn}/group", dependencies=[Depends(require_token)])
async def company_group(request: Request, inn: Inn,
                        onlyBankClients: Annotated[bool, Query()] = False):
    return await _proxy(request, f"{settings.group_companies_url}/v1/companies/{inn}/group",
                        {"onlyBankClients": str(onlyBankClients).lower()})


@app.get("/v1/companies/{inn}/scoring", dependencies=[Depends(require_token)])
async def company_scoring(request: Request, inn: Inn):
    return await _proxy(request, f"{settings.scoring_url}/v1/companies/{inn}/scoring")
