from flask import Blueprint, current_app, redirect, url_for, render_template, request, flash

from ..extensions import db
from ..models import Interaction
from ..auth import current_user

bp = Blueprint("videos", __name__)


@bp.route("/")
def home():
    user = current_user()
    if user:
        liked_ids = [
            i.video_id
            for i in Interaction.query.filter_by(user_id=user.id).all()
        ]
        recommendations = current_app.extensions["recommender"].recommend_for_user(liked_ids)
    else:
        recommendations = current_app.extensions["recommender"].trending()

    return render_template(
        "home.html",
        recommendations=recommendations,
        all_videos=current_app.extensions["recommender"].all_videos(),
    )


@bp.route("/video/<int:video_id>")
def video_detail(video_id):
    video = current_app.extensions["recommender"].get_video(video_id)
    if not video:
        flash("Video not found.", "danger")
        return redirect(url_for("videos.home"))

    user = current_user()
    if user:
        db.session.add(
            Interaction(user_id=user.id, video_id=video_id, action="watch")
        )
        db.session.commit()

    similar = current_app.extensions["recommender"].recommend_for_video(video_id)
    return render_template("video.html", video=video, similar=similar)


@bp.route("/like/<int:video_id>", methods=["POST"])
def like_video(video_id):
    user = current_user()
    if not user:
        flash("Please log in with Google to like videos.", "warning")
        return redirect(url_for("auth.login"))

    db.session.add(Interaction(user_id=user.id, video_id=video_id, action="like"))
    db.session.commit()
    flash("Added to your liked videos — recommendations updated!", "success")
    return redirect(url_for("videos.video_detail", video_id=video_id))


@bp.route("/search")
def search():
    query = request.args.get("q", "")
    results = current_app.extensions["recommender"].search(query)
    return render_template("search.html", results=results, query=query)
