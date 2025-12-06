from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    basic_auth_username: str = "admin"
    basic_auth_password: str
    database_url: str = "sqlite:///./airia.db"
    logging_level: str = "INFO"
    sql_echo: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.basic_auth_password:
        raise ValueError("BASIC_AUTH_PASSWORD must be set")
    return settings
