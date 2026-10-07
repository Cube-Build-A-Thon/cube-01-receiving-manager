from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from backend.app.core.config import get_settings

_BEARER = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    operator_id: str
    organization_id: str


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_BEARER)],
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    secret = get_settings().auth_jwt_secret
    if len(secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is not configured.",
        )

    try:
        claims = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "organization_id"]},
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    operator_id = claims.get("sub")
    organization_id = claims.get("organization_id")
    if (
        not isinstance(operator_id, str)
        or not operator_id.strip()
        or not isinstance(organization_id, str)
        or not organization_id.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token must identify an operator and organization.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthenticatedPrincipal(
        operator_id=operator_id.strip(),
        organization_id=organization_id.strip(),
    )
