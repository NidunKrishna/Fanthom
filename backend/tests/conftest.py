"""In-memory repository doubles keep unit tests independent of Aura."""
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app


class MemoryRepository:
    """Implement the persistence contract for authentication and API tests."""
    def __init__(self):
        self.users = {}
        self.reactions = {}
        self.records = [
            {'id': str(i), 'title': f'Python pipeline {i}', 'description': 'Airflow programming', 'tags': 'python airflow', 'category': '28'}
            for i in range(1, 10)
        ]

    def ensure_user(self, username, name):
        self.users[username] = name

    def videos(self):
        return self.records

    def preferences(self, username):
        return dict(self.reactions.get(username, {}))

    def react(self, username, video_id, reaction):
        if username not in self.users or not any(video['id'] == video_id for video in self.records):
            return False
        preferences = self.reactions.setdefault(username, {})
        if reaction == 'none':
            preferences.pop(video_id, None)
        else:
            preferences[video_id] = reaction
        return True


@pytest.fixture
def client():
    return TestClient(create_app(Settings(jwt_secret='test-key-' * 8), repository=MemoryRepository()))
