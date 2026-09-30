"""Integration checks for application wiring after package restructuring."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from vidrec import create_app
from vidrec.config import PROJECT_ROOT
from vidrec.extensions import db
from vidrec.models import Interaction, User


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_public_pages_and_redirects(self):
        for path in ["/", "/video/1", "/search?q=python", "/static/style.css"]:
            with self.subTest(path=path):
                with self.client.get(path) as response:
                    self.assertEqual(response.status_code, 200)
        for path, target in [("/profile", "/login"), ("/video/999999", "/")]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, target)
        self.assertEqual(self.client.post("/like/1").location, "/login")

    def test_authenticated_history_and_logout(self):
        with self.app.app_context():
            user = User(google_id="test", email="test@example.com", name="Test")
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        with self.client.session_transaction() as session:
            session["user_id"] = user_id
        self.assertEqual(self.client.get("/video/1").status_code, 200)
        self.assertEqual(self.client.post("/like/1").location, "/video/1")
        self.assertEqual(self.client.get("/").status_code, 200)
        profile = self.client.get("/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b"test@example.com", profile.data)
        with self.app.app_context():
            self.assertEqual([i.action for i in Interaction.query.order_by(Interaction.id)],
                             ["watch", "like"])
        self.assertEqual(self.client.get("/logout").location, "/")
        self.assertEqual(self.client.get("/profile").location, "/login")

    def test_oauth_routes(self):
        google = self.app.extensions["oauth"].google
        with patch.object(google, "authorize_redirect", return_value="oauth redirect") as redirect:
            self.assertEqual(self.client.get("/login").status_code, 200)
            redirect.assert_called_once_with("http://localhost/auth/callback")
        token = {"userinfo": {"sub": "google-test", "email": "oauth@example.com", "name": "OAuth Test"}}
        with patch.object(google, "authorize_access_token", return_value=token):
            for _ in range(2):
                self.assertEqual(self.client.get("/auth/callback").location, "/")
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(google_id="google-test").count(), 1)
        with self.client.session_transaction() as session:
            self.assertIn("user_id", session)

    def test_paths_and_multiple_app_instances(self):
        previous = Path.cwd()
        try:
            os.chdir(PROJECT_ROOT / "data")
            other = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
            self.assertEqual(Path(other.instance_path), PROJECT_ROOT / "instance")
            self.assertEqual(other.test_client().get("/").status_code, 200)
            with other.app_context():
                self.assertEqual(User.query.count(), 0)
                db.session.remove()
                db.engine.dispose()
            self.assertIsNot(other.extensions["recommender"], self.app.extensions["recommender"])
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
