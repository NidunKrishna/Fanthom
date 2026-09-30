"""Configuration loaded after the project environment file."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def default_config():
    return {
        "SECRET_KEY": os.getenv("FLASK_SECRET_KEY", "dev-secret-key"),
        "SQLALCHEMY_DATABASE_URI": "sqlite:///app.db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "VIDEO_CATALOG_PATH": PROJECT_ROOT / "data" / "videos.csv",
    }
