"""
Auth dependencies — Dainik-Vidya
Reusable FastAPI dependencies for JWT-based auth.
"""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from core.logger import get_logger

logger = get_logger()

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-dainik-vidya-key-change-me")
ALGORITHM = "HS256"

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Decode JWT and return user info. Raises 401 if missing/invalid."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — please log in.",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"email": email}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired — please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Optional[dict]:
    """Same as get_current_user but returns None for guests (no 401)."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        return {"email": email}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
