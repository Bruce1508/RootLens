import secrets
from typing import Annotated

from fastapi import Header, HTTPException

from app.core.config import Settings


def require_api_key(authorization: Annotated[str | None, Header()] = None) -> None:
    """Phase 4 minimum-credible-set auth: a single shared bearer token on
    every mutating investigation route. Fails closed — an unconfigured
    server-side key denies every request rather than letting them all
    through unauthenticated."""
    settings = Settings()
    if not settings.api_key:
        raise HTTPException(status_code=403, detail="API key not configured")

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = authorization.removeprefix("Bearer ")
    if not secrets.compare_digest(token, settings.api_key):
        raise HTTPException(status_code=403, detail="invalid bearer token")
