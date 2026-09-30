"""Flask application factory."""
from flask import Flask
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

from .config import PROJECT_ROOT, default_config
from .extensions import db


def create_app(test_config=None):
    load_dotenv(PROJECT_ROOT / ".env")
    app = Flask(__name__, instance_path=str(PROJECT_ROOT / "instance"))
    app.config.from_mapping(default_config())
    if test_config is not None:
        app.config.update(test_config)

    from .auth import inject_user
    from .routes import auth, profile, videos
    from .services.recommender import VideoRecommender

    db.init_app(app)
    with app.app_context():
        db.create_all()

    oauth = OAuth(app)
    app.extensions["oauth"] = oauth
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    app.extensions["recommender"] = VideoRecommender(app.config["VIDEO_CATALOG_PATH"])
    app.context_processor(inject_user)
    app.register_blueprint(auth.bp)
    app.register_blueprint(videos.bp)
    app.register_blueprint(profile.bp)
    return app
