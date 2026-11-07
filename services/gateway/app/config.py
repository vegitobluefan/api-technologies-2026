from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gateway_token: str = "change-me"
    client_info_url: str = "http://client-info:8004"
    group_companies_url: str = "http://group-companies:8005"
    scoring_url: str = "http://scoring:8002"
    upstream_timeout_sec: float = 0.9   # требование: ответ (в т.ч. 503/504) быстрее 1 с


settings = Settings()
