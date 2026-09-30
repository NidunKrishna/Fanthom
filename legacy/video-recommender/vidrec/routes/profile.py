from flask import Blueprint, current_app, redirect, url_for, render_template

from ..models import Interaction
from ..auth import current_user

bp = Blueprint("profile", __name__)


@bp.route("/profile")
def profile():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))

    interactions = Interaction.query.filter_by(user_id=user.id).order_by(
        Interaction.created_at.desc()
    ).all()

    history = []
    for i in interactions:
        v = current_app.extensions["recommender"].get_video(i.video_id)
        if v:
            v = dict(v)
            v["action"] = i.action
            history.append(v)

    return render_template("profile.html", user=user, history=history)
