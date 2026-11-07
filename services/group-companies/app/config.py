from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://spark:spark@postgres:5432/spark"


settings = Settings()
