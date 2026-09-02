from typing import Annotated, Literal

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


class Settings(BaseSettings):
    # Local dev commands run with cwd=apps/api (see Makefile), where the
    # repo-root .env lives two levels up. Docker Compose injects env vars
    # directly instead, so a missing file here (e.g. in-container) is fine
    # — pydantic-settings silently skips absent env_file paths, and real
    # environment variables always take precedence over file contents.
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    database_url: str
    database_url_readonly: str
    environment: Literal["development", "test", "production"] = "development"
    cors_origins: Annotated[list[str], NoDecode, BeforeValidator(_split_csv)] = [
        "http://localhost:3000"
    ]
