from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    spark_url: str
    spark_wsdl: str
    spark_login: str
    spark_password: str
    database_url: str
    team_api_key: str = ""           # СПАРК ключ не использует (логин и пароль); поле оставлено для общего .env
    spark_ns: str = ""               # namespace SOAP-заголовка; пусто = взять из WSDL
    mock_scenario: str = ""
    rate_limit_rps: int = 5          # лимит СПАРК на всю команду
    request_timeout: float = 15.0
    incremental_interval_sec: int = 300
    spark_page_size: int = 0         # PageSize для списков; 0 = не передавать (сервер отдаёт по 100)
    scd2_valid_from: str = "actual"  # valid_from версии: "actual" = ActualDate из отчёта СПАРК, "load" = время загрузки
    loader_workers: int = 8          # потоков при загрузке, все ждут общий лимитер
    loader_dry_run: bool = False     # true: в БД ничего не пишем (проверка загрузки и разбора до готовности SCD2)


settings = Settings()


def mock_headers() -> dict:
    """X-Mock-Scenario добавляем ТОЛЬКО если переменная задана."""
    return {"X-Mock-Scenario": settings.mock_scenario} if settings.mock_scenario else {}
