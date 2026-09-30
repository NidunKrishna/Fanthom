# Aphrodite.ai

An editorial React experience with a cinematic introduction and a FastAPI authentication service.

## Structure

```text
backend/
  app/
    main.py                # App factory, CORS, security headers, health check
    api/auth.py            # Login and protected identity routes
    core/config.py         # Environment configuration
    core/security.py       # Password hashing and JWT signing/validation
  tests/test_auth.py
  .env.example
  requirements.txt
  requirements-dev.txt
frontend/
  src/
    components/            # SplashIntro, LoginCard, PrivateSpace
    lib/api.js             # HTTP client with timeout/error handling
    App.jsx                # Experience and in-memory session lifecycle
    main.jsx
    styles.css             # Tailwind v4 + editorial styling
  tests/auth.spec.js        # Browser integration checks
  .env.example
  package.json
  package-lock.json
  vite.config.js
legacy/video-recommender/  # Original Flask project, preserved separately
```

## Run locally

Requires Python 3.11+ and Node.js 22.12+ (Node 24 is also supported).
Open two terminals in this repository.

**Terminal 1 — API (PowerShell):**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy with `cp .env.example .env`.
If PowerShell activation is unavailable, use `.\.venv\Scripts\python.exe` directly.

**Terminal 2 — frontend:**

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Demo credentials are **admin / root** and are prefilled.
The intro reveals the wordmark for 1.5 seconds, holds for 1.8 seconds, then dissolves over 1 second.
It can be skipped or replayed. Reduced-motion preferences shorten the introduction and disable spatial effects.

Vite proxies `/api` to port 8000. For separately hosted deployments, copy `frontend/.env.example`
to `frontend/.env` and set `VITE_API_URL` before building. The backend permits localhost/127.0.0.1
on port 5173 by default; configure `CORS_ORIGINS` for other exact origins.

## API

- `POST /api/auth/login` — JSON `{"username":"admin","password":"root"}`; returns
  `{"access_token":"<signed JWT>","token_type":"bearer","expires_in":1800}`.
- `GET /api/auth/me` — requires `Authorization: Bearer <token>`; returns username and expiry.
- `GET /api/health` — process health.
- Interactive API documentation: **http://127.0.0.1:8000/docs**.

Incorrect credentials return HTTP 401 with a human-readable `detail`. Missing or invalid fields
return 422. Login requests are limited to 10 per minute per client IP; exceeding this returns 429.

## Authentication behavior

Passwords are verified against an Argon2 hash. The demo password is hashed at startup; a configured
`ADMIN_PASSWORD_HASH` takes precedence. JWT validation pins HS256 and checks signature, expiration,
issuer, audience, and required claims. The frontend checks `/api/auth/me` before showing the private
space. Tokens remain in React memory; refresh and sign-out discard the client token. Sessions end
automatically after 30 minutes. The welcome screen is the authenticated destination; no AI inference
or additional workspace features are implied.

A random signing key is generated for local development if `JWT_SECRET` is absent, so restarting
invalidates tokens. Set a persistent secret for stable sessions. Sign-out clears the browser session;
issued bearer tokens remain valid until expiry (there is no server-side token revocation).

## Production configuration

Set `APP_ENV=production`, an explicit random `JWT_SECRET` (at least 32 characters),
`ADMIN_PASSWORD_HASH`, and exact `CORS_ORIGINS`. The backend refuses production startup without
the secret and hash. Generate values locally:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from getpass import getpass; from pwdlib import PasswordHash; print(PasswordHash.recommended().hash(getpass('Password: ')))"
```

Set `VITE_SHOW_DEMO_CREDENTIALS=false` before building to hide the demo hint and empty the fields.
Serve over HTTPS and route `/api` to the backend, or set `VITE_API_URL` to its HTTPS origin.
The login limiter is process-local; use a shared limiter and trusted proxy configuration for
multi-worker deployments. This is a single configured account, not a registration/user-management system.

```powershell
cd frontend
npm run build
```

Deploy `frontend/dist/` with an SPA-capable static host. `npm run preview` previews the built assets;
it needs `VITE_API_URL` configured at build time or a host that proxies `/api`.
Fonts load from Google Fonts, with local serif/sans-serif fallbacks when offline.

## Checks

Backend, from `backend/` with its Python environment active:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Browser checks, from `frontend/`, with the API running on port 8000:

```powershell
npx playwright install chromium
npm test
```

Playwright starts Vite automatically. Tests cover the intro, real successful and failed logins,
password visibility, sign-out, network failure, mobile overflow, and reduced motion.

## Previous application

The Flask video recommender is preserved in `legacy/video-recommender/`, including its own README
and dependency list. Run its `app.py` from that directory. A database snapshot is included in its
ignored `instance/` directory. The original root `instance/app.db` was in use during migration
and remains untouched; the legacy copy is a snapshot, not a live synchronized database.

Implementation references: [FastAPI JWT authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[Tailwind's Vite integration](https://tailwindcss.com/docs/installation/using-vite),
and [Motion accessibility](https://motion.dev/docs/react-use-reduced-motion).
