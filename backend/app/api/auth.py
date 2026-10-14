"""Authenticate the configured account, persist its profile, and verify JWTs."""
import secrets
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ..core.security import decode_token, issue_token, password_hasher

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    """Bounded login credentials; profile names come from backend settings."""
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    """Bearer credentials returned after password and graph profile checks."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginLimiter:
    """Bounded, process-local limiter; use a shared store for multiple workers."""

    def __init__(self):
        """Initialize bounded client queues and their synchronization lock."""
        self.attempts = OrderedDict()
        self.lock = Lock()

    def check(self, key):
        """Allow at most ten attempts per client in a rolling sixty-second window."""
        now = monotonic()
        with self.lock:
            entries = self.attempts.setdefault(key, deque())
            self.attempts.move_to_end(key)
            while entries and entries[0] <= now - 60:
                entries.popleft()
            if len(entries) >= 10:
                raise HTTPException(429, "A moment of pause. Please try again in one minute.",
                                    headers={"Retry-After": "60"})
            entries.append(now)
            if len(self.attempts) > 10000:
                self.attempts.popitem(last=False)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response):
    """Verify credentials, upsert the graph profile, then issue a signed token."""
    request.app.state.limiter.check(request.client.host if request.client else "unknown")
    settings = request.app.state.settings
    password_valid = password_hasher.verify(payload.password, request.app.state.password_hash)
    username_valid = secrets.compare_digest(payload.username.encode(), settings.username.encode())
    if not (password_valid and username_valid):
        raise HTTPException(401, "Those credentials don't quite match. Please try again.",
                            headers={"WWW-Authenticate": "Bearer"})
    request.app.state.repository.ensure_user(settings.username, settings.display_name or settings.username)
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(access_token=issue_token(settings.username, settings),
                         expires_in=settings.token_minutes * 60)


@router.get("/me")
def me(request: Request, response: Response,
       credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """Validate the bearer token and return the authenticated account identity."""
    error = HTTPException(401, "Your session has ended. Please sign in again.",
                          headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise error
    try:
        claims = decode_token(credentials.credentials, request.app.state.settings)
        if claims["sub"] != request.app.state.settings.username:
            raise error
    except jwt.InvalidTokenError:
        raise error from None
    response.headers["Cache-Control"] = "no-store"
    return {"username": claims["sub"], "name": request.app.state.settings.display_name or claims["sub"], "expires_at": claims["exp"]}
