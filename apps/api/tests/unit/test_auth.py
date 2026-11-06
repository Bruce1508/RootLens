from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.auth import require_api_key
from app.core.config import Settings


def _settings_with_key(key: str | None) -> Settings:
    return Settings(database_url="x", database_url_readonly="x", api_key=key)


def test_require_api_key_raises_403_when_server_key_unconfigured() -> None:
    with patch("app.core.auth.Settings", return_value=_settings_with_key(None)):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(authorization="Bearer anything")

    assert exc_info.value.status_code == 403


def test_require_api_key_raises_401_when_header_missing() -> None:
    with patch("app.core.auth.Settings", return_value=_settings_with_key("secret-token")):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(authorization=None)

    assert exc_info.value.status_code == 401


def test_require_api_key_raises_401_when_header_not_bearer_scheme() -> None:
    with patch("app.core.auth.Settings", return_value=_settings_with_key("secret-token")):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(authorization="Basic secret-token")

    assert exc_info.value.status_code == 401


def test_require_api_key_raises_403_when_token_is_wrong() -> None:
    with patch("app.core.auth.Settings", return_value=_settings_with_key("secret-token")):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(authorization="Bearer wrong-token")

    assert exc_info.value.status_code == 403


def test_require_api_key_passes_when_token_matches() -> None:
    with patch("app.core.auth.Settings", return_value=_settings_with_key("secret-token")):
        require_api_key(authorization="Bearer secret-token")
