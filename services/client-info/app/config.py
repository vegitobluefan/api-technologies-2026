from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://spark:spark@postgres:5432/spark"
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 3600


settings = Settings()
