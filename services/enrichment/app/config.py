from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    abs_url: str
    team_api_key: str
    mock_scenario: str = ""
    cache_ttl_seconds: int = 3600

settings = Settings()

def abs_headers() -> dict:
    h = {"X-API-Key": settings.team_api_key}
    if settings.mock_scenario:           # пусто = заголовок не отправляем
        h["X-Mock-Scenario"] = settings.mock_scenario
    return h
