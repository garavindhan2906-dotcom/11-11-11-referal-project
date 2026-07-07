from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    BASE_URL: str = "https://11-11-11.shop"
    ADMIN_SECRET_KEY: str = "admin-secret"

    class Config:
        env_file = ".env"


settings = Settings()
