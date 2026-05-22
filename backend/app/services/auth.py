"""Supabase JWT verification.

The frontend ships the user's Supabase access token in the Authorization
header. We verify it locally (HS256 with the project JWT secret) rather than
round-tripping to Supabase on every request. This is the same trust model
Supabase's own PostgREST uses.
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings


class CurrentUser:
    def __init__(self, user_id: str, email: str | None) -> None:
        self.id = user_id
        self.email = email


async def require_user(request: Request) -> CurrentUser:
    auth_header = request.headers.get("authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token,
            get_settings().supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}") from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token missing sub")
    return CurrentUser(user_id=sub, email=payload.get("email"))


User = Annotated[CurrentUser, Depends(require_user)]
