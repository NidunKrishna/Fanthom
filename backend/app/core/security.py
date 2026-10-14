"""Hash passwords and sign/validate expiring application JWTs."""
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from .config import Settings

password_hasher = PasswordHash.recommended()


def issue_token(username: str, settings: Settings) -> str:
    """Sign an identity token with the configured lifetime, issuer, and audience."""
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.token_minutes),
        "iss": "aphrodite.ai",
        "aud": "aphrodite-web",
        "jti": secrets.token_urlsafe(16),
    }, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, settings: Settings) -> dict:
    """Verify HS256 signature, expiry, issuer, audience, and required claims."""
    return jwt.decode(
        token, settings.jwt_secret, algorithms=["HS256"],
        issuer="aphrodite.ai", audience="aphrodite-web",
        options={"require": ["sub", "iat", "exp", "iss", "aud", "jti"]},
    )
