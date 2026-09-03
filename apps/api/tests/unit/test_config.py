import pytest
from pydantic import ValidationError


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:pw@localhost:5432/rootlens")
    monkeypatch.setenv(
        "DATABASE_URL_READONLY", "postgresql+psycopg://ro:pw@localhost:5432/rootlens"
    )

    from app.core.config import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.database_url == "postgresql+psycopg://app:pw@localhost:5432/rootlens"
    assert settings.database_url_readonly == "postgresql+psycopg://ro:pw@localhost:5432/rootlens"
    assert settings.environment == "development"
    assert settings.cors_origins == ["http://localhost:3000"]


def test_settings_parses_comma_separated_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:pw@localhost:5432/rootlens")
    monkeypatch.setenv(
        "DATABASE_URL_READONLY", "postgresql+psycopg://ro:pw@localhost:5432/rootlens"
    )
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")

    from app.core.config import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:3001"]


def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_READONLY", raising=False)

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_defaults_ollama_base_url_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:pw@localhost:5432/rootlens")
    monkeypatch.setenv(
        "DATABASE_URL_READONLY", "postgresql+psycopg://ro:pw@localhost:5432/rootlens"
    )
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    from app.core.config import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "qwen3:8b"
