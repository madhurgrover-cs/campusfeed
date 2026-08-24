"""Service-scoped auth for the /ingest endpoint only.

Deliberately separate from app.auth.dependencies (User/JWT/roles) - this token
grants no access to any other endpoint, it is checked in isolation here.
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

ingest_bearer_scheme = HTTPBearer(auto_error=False)


def verify_ingest_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(ingest_bearer_scheme),
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing ingest service token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected = get_settings().ingest_service_token
    if not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ingest service token",
        )
