from flask import Blueprint, current_app, redirect, url_for, session, flash

from ..extensions import db
from ..models import User

bp = Blueprint("auth", __name__)


@bp.route("/login")
def login():
    redirect_uri = url_for("auth.auth_callback", _external=True)
    return current_app.extensions["oauth"].google.authorize_redirect(redirect_uri)


@bp.route("/auth/callback")
def auth_callback():
    token = current_app.extensions["oauth"].google.authorize_access_token()
    user_info = token.get("userinfo") or current_app.extensions["oauth"].google.parse_id_token(token)

    google_id = user_info["sub"]
    email = user_info["email"]
    name = user_info.get("name", email)
    picture = user_info.get("picture", "")

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User(google_id=google_id, email=email, name=name, picture=picture)
        db.session.add(user)
        db.session.commit()

    session["user_id"] = user.id
    flash(f"Welcome, {user.name}!", "success")
    return redirect(url_for("videos.home"))


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("videos.home"))
