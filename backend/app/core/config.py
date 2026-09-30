import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    username: str = field(default_factory=lambda: os.getenv("ADMIN_USERNAME", "admin"))
    password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", "root"))
    password_hash: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD_HASH", ""))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET") or secrets.token_urlsafe(48))
    token_minutes: int = 30
    origins: list[str] = field(default_factory=lambda: [
        origin.strip() for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if origin.strip()
    ])

    def __post_init__(self):
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters.")
        if self.environment == "production":
            if not os.getenv("JWT_SECRET") or not self.password_hash:
                raise ValueError("Production requires JWT_SECRET and ADMIN_PASSWORD_HASH.")
            if "*" in self.origins:
                raise ValueError("Production requires explicit CORS origins.")
