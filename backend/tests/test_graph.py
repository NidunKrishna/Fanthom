"""Check graph query mapping, cache behavior, and driver error boundaries."""
from unittest.mock import Mock
from threading import Event
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from app.core.config import Settings
from app.main import create_app
from app.repositories.graph import GraphRepository
from app.services.feed import FeedService
from conftest import MemoryRepository


def test_graph_mapping_and_parameterized_exclusive_feedback():
    database = Mock()
    database.read.return_value = [{'id': 'abc', 'title': 'Python', 'description': None, 'category': 28, 'hashtags': ['code'], 'topics': ['python'], 'creators': ['Creator'], 'playback_url': 'https://example.com/video.mp4'}]
    repository = GraphRepository(database)
    assert repository.videos()[0]['tags'] == 'code python Creator'
    assert repository.videos()[0]['playback_url'].endswith('.mp4')
    repository.ensure_user('alice', 'Alice')
    repository.ensure_user('alice', 'Alice')
    assert sum('CREATE CONSTRAINT' in call.args[0] for call in database.write.call_args_list) == 1
    database.write.return_value = [{'id': 'abc'}]
    assert repository.react('alice', 'abc', 'dislike')
    query = database.write.call_args.args[0]
    assert 'DELETE edge' in query and 'r:DISLIKED' in query
    assert database.write.call_args.kwargs == {'username': 'alice', 'video_id': 'abc'}
    repository.react('alice', 'abc', 'none')
    assert 'MERGE (u)-' not in database.write.call_args.args[0]


def test_catalog_cache_preferences_and_database_failure(client):
    repository = MemoryRepository()
    repository.videos = Mock(wraps=repository.videos)
    service = FeedService(repository)
    service.recommendations('admin')
    repository.reactions['admin'] = {'1': 'dislike'}
    assert all(video['id'] != '1' for video in service.recommendations('admin'))
    repository.videos.assert_called_once()
    service._loaded_at = 0
    service.recommendations('admin')
    assert repository.videos.call_count == 2
    token = client.post('/api/auth/login', json={'username': 'admin', 'password': 'root'}).json()['access_token']
    client.app.state.repository.videos = Mock(side_effect=ServiceUnavailable('private details'))
    response = client.get('/api/videos', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 503 and 'private details' not in response.text
    client.app.state.repository.ensure_user = Mock(side_effect=ServiceUnavailable('private details'))
    assert client.post('/api/auth/login', json={'username': 'admin', 'password': 'root'}).status_code == 503


def test_missing_database_does_not_fall_back_to_csv():
    client = TestClient(create_app(Settings(neo4j_uri='')))
    assert client.post('/api/auth/login', json={'username': 'admin', 'password': 'root'}).status_code == 503


def test_youtube_ids_supply_missing_links_and_previews_sort_last():
    database = Mock()
    base = {'title': 'Video', 'description': '', 'category': '28', 'hashtags': [], 'topics': [], 'creators': []}
    database.read.return_value = [
        {**base, 'id': 'abc123', 'playback_url': None},
        {**base, 'id': '1i0hqFR5hKs', 'playback_url': None},
        {**base, 'id': 'custom', 'playback_url': 'https://example.com/video.mp4'},
    ]
    videos = GraphRepository(database).videos()
    assert videos[0]['playback_url'] == 'https://www.youtube.com/watch?v=1i0hqFR5hKs'
    assert videos[1]['playback_url'] == 'https://example.com/video.mp4'
    assert videos[2]['id'] == 'abc123' and videos[2]['playback_url'] is None


def test_background_polling_retries_and_discovers_new_records():
    repository = MemoryRepository()
    service = FeedService(repository, poll_seconds=0.01)
    repository.videos = Mock(side_effect=[ServiceUnavailable('temporary'), repository.records, [*repository.records, {'id': 'new', 'title': 'New graph video'}]])
    updated = Event()
    original_refresh = service.refresh

    def refresh():
        original_refresh()
        if 'new' in service._engine.id_to_index:
            updated.set()

    service.refresh = refresh
    service.start()
    service.start()  # Starting twice must not create another worker.
    try:
        assert updated.wait(timeout=3)
        assert 'new' in service.engine().id_to_index
    finally:
        service.stop()
    assert not service._worker.is_alive()


def test_unchanged_poll_reuses_vectors_and_lifespan_stops_worker():
    repository = MemoryRepository()
    service = FeedService(repository)
    service.refresh()
    original = service.engine()
    service.refresh()
    assert service.engine() is original
    app = create_app(Settings(), repository=repository)
    with TestClient(app):
        assert app.state.feed._worker.is_alive()
    assert not app.state.feed._worker.is_alive()
