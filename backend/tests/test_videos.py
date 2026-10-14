"""Verify protected graph feeds, persistent feedback, and user isolation."""
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings


def test_recommendations_require_authentication(client):
    assert client.get('/api/videos').status_code == 401
    assert client.get('/api/videos', headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_catalog_and_similar_recommendations(client):
    token = client.post('/api/auth/login', json={'username': 'admin', 'password': 'root'}).json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/api/videos', headers=headers)
    assert response.status_code == 200
    videos = response.json()['videos']
    assert len(videos) == 8
    selected = videos[0]['id']
    similar = client.get(f'/api/videos?video_id={selected}', headers=headers)
    assert similar.status_code == 200
    assert len(similar.json()['videos']) == 5
    assert all(video['id'] != selected for video in similar.json()['videos'])
    assert client.get('/api/videos?video_id=999999', headers=headers).status_code == 404


def test_reactions_and_user_isolation(client):
    token = client.post('/api/auth/login', json={'username': 'admin', 'password': 'root'}).json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    assert client.app.state.repository.users['admin'] == 'admin'
    assert client.post('/api/videos/reaction', json={'video_id': '1', 'reaction': 'like'}).status_code == 401
    for reaction in ('like', 'dislike', 'none'):
        response = client.post('/api/videos/reaction', headers=headers, json={'video_id': '1', 'reaction': reaction})
        assert response.status_code == 200
        feed = client.get('/api/videos', headers=headers).json()['videos']
        if reaction == 'dislike':
            assert all(video['id'] != '1' for video in feed)
        else:
            assert next(video for video in feed if video['id'] == '1')['reaction'] == (None if reaction == 'none' else reaction)
    assert client.post('/api/videos/reaction', headers=headers, json={'video_id': '1', 'reaction': 'invalid'}).status_code == 422
    assert client.post('/api/videos/reaction', headers=headers, json={'video_id': 'missing', 'reaction': 'like'}).status_code == 404
    assert client.post('/api/videos/reaction', headers=headers, json={'video_id': '1', 'reaction': 'like', 'username': 'someone-else'}).status_code == 422
    assert client.app.state.repository.preferences('someone-else') == {}
    editor = TestClient(create_app(Settings(username='editor', password='secret'), repository=client.app.state.repository))
    editor_token = editor.post('/api/auth/login', json={'username': 'editor', 'password': 'secret'}).json()['access_token']
    feed = editor.get('/api/videos', headers={'Authorization': f'Bearer {editor_token}'}).json()['videos']
    assert all(video['reaction'] is None for video in feed)
