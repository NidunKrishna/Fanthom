import jwt
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings

@pytest.fixture
def client():
    return TestClient(create_app(Settings(jwt_secret='test-key-' * 8)))

def test_login_and_protected_identity(client):
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'root'})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['token_type'] == 'bearer'
    assert data['expires_in'] == 1800
    identity = client.get('/api/auth/me', headers={'Authorization': f"Bearer {data['access_token']}"})
    assert identity.status_code == 200
    assert identity.json()['username'] == 'admin'

@pytest.mark.parametrize('username,password', [('admin', 'wrong'), ('wrong', 'root')])
def test_wrong_credentials(client, username, password):
    response = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 401
    assert 'access_token' not in response.json()
    assert isinstance(response.json()['detail'], str)

@pytest.mark.parametrize('token', ['', 'invalid', 'eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.'])
def test_reject_missing_and_invalid_tokens(client, token):
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401

def test_expired_and_wrongly_signed_tokens(client):
    settings = client.app.state.settings
    now = datetime.now(timezone.utc)
    claims = {'sub':'admin', 'iat':now-timedelta(hours=2), 'exp':now-timedelta(hours=1),
              'iss':'aphrodite.ai', 'aud':'aphrodite-web', 'jti':'test'}
    expired = jwt.encode(claims, settings.jwt_secret, algorithm='HS256')
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {expired}'}).status_code == 401
    claims['exp'] = now + timedelta(hours=1)
    forged = jwt.encode(claims, 'different-key-' * 5, algorithm='HS256')
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {forged}'}).status_code == 401

def test_cors_and_validation(client):
    headers = {'Origin':'http://localhost:5173', 'Access-Control-Request-Method':'POST',
               'Access-Control-Request-Headers':'content-type'}
    response = client.options('/api/auth/login', headers=headers)
    assert response.headers['access-control-allow-origin'] == headers['Origin']
    headers['Origin'] = 'https://untrusted.example'
    assert 'access-control-allow-origin' not in client.options('/api/auth/login', headers=headers).headers
    assert client.post('/api/auth/login', json={}).status_code == 422

def test_rate_limit(client):
    for _ in range(10):
        assert client.post('/api/auth/login', json={'username':'admin','password':'bad'}).status_code == 401
    response = client.post('/api/auth/login', json={'username':'admin','password':'root'})
    assert response.status_code == 429
    assert response.headers['retry-after'] == '60'

def test_environment_credentials():
    client = TestClient(create_app(Settings(username='editor', password='custom-password', jwt_secret='test-key-'*8)))
    assert client.post('/api/auth/login', json={'username':'admin','password':'root'}).status_code == 401
    assert client.post('/api/auth/login', json={'username':'editor','password':'custom-password'}).status_code == 200

def test_production_rejects_demo_configuration(monkeypatch):
    monkeypatch.delenv('JWT_SECRET', raising=False)
    with pytest.raises(ValueError, match='Production requires'):
        Settings(environment='production', password_hash='')
