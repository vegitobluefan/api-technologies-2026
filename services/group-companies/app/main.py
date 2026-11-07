"""Group Companies Service (владелец: Павел). Контракт: contracts/group-companies-service/openapi.yaml."""
from typing import Annotated

from fastapi import FastAPI, Path, Query

from platform_common.errors import INN_PATTERN, ApiError, install
from platform_common.mapping import to_company_group

from . import repository

app = FastAPI(title="Group Companies Service")
install(app)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/companies/{inn}/group")
def company_group(inn: Annotated[str, Path(pattern=INN_PATTERN)],
                  onlyBankClients: Annotated[bool, Query()] = False):
    data = repository.get_group(inn)
    if data is None:
        raise ApiError(404, "COMPANY_NOT_FOUND", "Компания с таким ИНН не найдена")
    return to_company_group(inn, data["group_id"], data["group_name"], data["rows"],
                            onlyBankClients, data["data_as_of"])
