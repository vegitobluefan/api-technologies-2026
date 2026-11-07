"""Scoring Service (владелец: Фёдор). Контракт: contracts/scoring-service/openapi.yaml."""
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import FastAPI, Path

from platform_common.errors import INN_PATTERN, ApiError, install
from platform_common.mapping import iso_utc

from . import ml_client, repository
from .features import build_features

app = FastAPI(title="Scoring Service")
install(app)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/companies/{inn}/scoring")
def scoring(inn: Annotated[str, Path(pattern=INN_PATTERN)]):
    data = repository.load_company_for_scoring(inn)
    if data is None:
        raise ApiError(404, "COMPANY_NOT_FOUND", "Компания с таким ИНН не найдена")
    # TODO: дата расчёта для возраста — сегодня или data_as_of? Сверить с tools/expected.py
    numeric, categorical = build_features(data["company"], data["members"], as_of=date.today())
    result = ml_client.predict(inn, numeric, categorical)
    return {
        "inn": inn,
        "probability": result.score,
        "modelVersion": result.model_version,
        "scoredAt": iso_utc(datetime.now(timezone.utc)),
        "dataAsOf": iso_utc(data["data_as_of"]),
    }
