"""Session helpers shared by routes and templates."""
from flask import session

from .extensions import db
from .models import User


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def inject_user():
    return {"current_user": current_user()}
