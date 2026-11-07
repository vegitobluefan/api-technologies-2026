from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://spark:spark@postgres:5432/spark"
    ml_model_addr: str = "ml-model:50051"
    ml_timeout_sec: float = 2.0


settings = Settings()
