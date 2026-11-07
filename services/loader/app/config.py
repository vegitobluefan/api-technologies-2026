from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    spark_url: str
    spark_wsdl: str
    spark_login: str
    spark_password: str
    database_url: str
    mock_scenario: str = ""
    rate_limit_rps: int = 5
    request_timeout: float = 15.0
    incremental_interval_sec: int = 300

settings = Settings()

def mock_headers() -> dict:
    """X-Mock-Scenario добавляем ТОЛЬКО если переменная задана (zeep: transport.session.headers.update)."""
    return {"X-Mock-Scenario": settings.mock_scenario} if settings.mock_scenario else {}
