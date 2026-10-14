# Backend guide

The backend authenticates a configured account, stores its profile and reactions
in Neo4j, and recommends graph videos using TF-IDF. Neo4j is the only data source;
there is no CSV fallback. All application modules and their main operations have
docstrings describing their responsibilities.

## Structure

```text
app/
  main.py                 Application wiring, middleware, error responses
  schemas.py              Validated request and public response models
  api/
    auth.py               Login, JWT identity checks, login rate limit
    videos.py             Protected feed and reaction routes
  core/
    config.py             Environment configuration
    security.py           Password hashing and JWT signing/verification
    database.py           Neo4j sessions and read/write transactions
  repositories/
    graph.py              Catalog, user, and reaction Cypher queries
  services/
    feed.py               Catalog cache and user-specific feed coordination
    recommender.py        Recommendation algorithm, independent of persistence
```

The former `services/neo4j_catalog.py` and `data/videos.csv` were removed. The
ranking engine no longer reads files or uses pandas. Unused search and history
helper methods were removed. Legacy Flask code is separate from this backend.

## Request flow

```text
Sign-in -> POST /api/auth/login
          -> Verify password and rate limit
          -> Create/update User node
          -> Return JWT
        -> GET /api/auth/me
          -> Validate token and return username, name, expiry
Frontend opens /feed
        -> GET /api/videos
          -> Validate JWT
          -> FeedService loads cached graph catalog
          -> Read current user's LIKED/DISLIKED relationships
          -> VideoRecommender ranks videos
          -> Return public metadata and saved reaction
Like/dislike -> POST /api/videos/reaction
          -> Validate JWT and request body
          -> Atomically replace/remove the user's reaction edge
```

`/feed` navigation is implemented in React, not as a backend redirect.

## Application and configuration

`main.create_app(settings=None, repository=None)` assembles dependencies. The
optional repository argument supports network-free unit tests. `app.state`
contains settings, the password hash, the login limiter, the graph repository,
and the feed service. The module-level `app` is imported by Uvicorn.

The app opens no database connection at import time. A valid login needs the
graph because it persists a profile; missing configuration/database failures
return HTTP 503. `/api/health` reports process liveness only.

Configuration is loaded from `backend/.env` with existing process environment
values taking precedence. Required graph settings are `NEO4J_URI`,
`NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE`.

Authentication settings:

| Setting | Purpose |
| --- | --- |
| `ADMIN_USERNAME` | Login identity and unique graph user key; defaults to `admin`. |
| `ADMIN_DISPLAY_NAME` | Human-readable `User.name`; defaults to username when empty. |
| `ADMIN_PASSWORD` | Development password; defaults to `root`. |
| `ADMIN_PASSWORD_HASH` | Preferred configured Argon2 hash. |
| `JWT_SECRET` | Signing key of at least 32 characters; random in development if absent. |
| `APP_ENV` | Production requires an explicit signing key and password hash. |
| `CORS_ORIGINS` | Exact frontend origins allowed by browser CORS policy. |

The login system still supports one configured account, not registration or a
multi-account directory. The graph and reaction API isolate preferences by the
verified username; changing the configured username addresses a different user.
A separate multi-user identity provider/login store would be needed for many
accounts to sign in simultaneously.

## Authentication and identity

`POST /api/auth/login` accepts a username and password. Pydantic validates their
lengths. The process-local limiter allows ten attempts per client IP per rolling
minute and returns HTTP 429 thereafter. Password verification uses pwdlib's
recommended Argon2 hasher; username comparison uses `secrets.compare_digest`.

After verification, `GraphRepository.ensure_user()` creates a uniqueness
constraint on `User.username` once per process and uses `MERGE` to save the
profile. The database account therefore needs schema and write permissions.
The JWT is issued only after profile persistence succeeds.

Tokens use HS256 and contain `sub`, `iat`, `exp`, `iss`, `aud`, and `jti`.
Validation pins the algorithm, signature, issuer, audience, expiry, and required
claims, then checks that the subject matches the configured account. The default
lifetime is 30 minutes. JWTs contain identity metadata, not passwords.

`GET /api/auth/me` returns username, display name, and expiry. The video routes
use `Depends(me)`, so identity is derived from the verified token. Reaction
bodies reject additional fields such as a client-supplied username.

Sign-out discards the frontend token; there is no server-side revocation list.
A randomly generated signing key invalidates old tokens when the app restarts.

## Graph repository and feedback

```text
(User {username, name, created_at, feedback_updated_at})
  -[:LIKED {updated_at}]->(Video {video_id, ...})
  -[:DISLIKED {updated_at}]->(Video {video_id, ...})

(Creator)-[:CREATED]->(Video)-[:HAS_TOPIC]->(Topic)
```

Only one reaction is stored for each user/video pair. Repeating Like is
idempotent at the API level. Switching to Dislike removes LIKED and creates
DISLIKED. Clicking the selected reaction again sends `none`, removing either
edge. Feedback timestamps are saved; passwords/JWTs are not stored in the graph.
Catalog-wide `Video.like_count` is existing metadata and is not incremented by
these personal reactions.

`GraphRepository.react()` runs the replacement in one write transaction. It first
updates the user node to acquire a write lock, then finds the video, collects and
deletes previous reaction edges, and merges the new fixed-type relationship.
The lock serializes concurrent reactions for the same user. Values are passed as
parameters; relationship types come from a fixed internal mapping.

Unknown videos or missing profiles return 404; no phantom videos are created.

## Catalog and media links

`GraphRepository.videos()` reads only `Video` nodes, joins optional creators and
topics, and orders by view count descending then video ID. It maps `video_id` to
string `id`, fills missing text fields, and combines hashtags/topic/creator names
into tags. The public response model omits internal ranking fields.

Store a full HTTPS video URL in `Video.link`. For compatibility the loader also
accepts `playback_url`, `video_url`, `video_link`, and `url`, in that priority order
after `link`. It returns the chosen value as `playback_url`.

Example update in Neo4j Query (replace both placeholders):

```cypher
MATCH (v:Video {video_id: 'YOUR_EXISTING_VIDEO_ID'})
SET v.link = 'https://www.youtube.com/watch?v=YOUR_VIDEO_ID'
RETURN v.video_id, v.link;
```

If a URL is missing, an 11-character YouTube-format video_id supplies a YouTube watch URL. Short sample IDs remain previews. Entries with playback links sort ahead of previews, retaining popularity order within each group. The frontend embeds recognized YouTube
watch/short/embed URLs, plays direct MP4/WebM/OGG/MOV links using a video element,
and opens other HTTPS links in a new tab. Unsafe/non-HTTPS links do not play.
Missing links and invalid-format IDs show a catalog preview. A link may still fail if the provider
restricts embedding or the video is unavailable. Only the active card's player is mounted, so scrolling away stops it. YouTube and direct video players request muted autoplay; browser/provider restrictions can still require pressing Play. Metadata sits below the player so its controls remain usable.

`FeedService` polls Neo4j immediately at API startup and every 10 seconds after
completed reads. Set `CATALOG_POLL_SECONDS` in `backend/.env` to change the backend
interval (1?3600 seconds). FastAPI's lifespan starts and stops the worker.

Polls are sequential and protected by a lock. New or modified catalog data rebuilds
the vectors; unchanged data reuses them. Failed background reads keep the last
good snapshot and retry on the next interval. If no snapshot exists, a feed request
attempts a load and can return HTTP 503. Each API worker has its own poller/cache.
Preferences are read per request.

The open frontend checks recommendations every 10 seconds, skips hidden tabs,
and appends newly returned videos without replacing the current ordering or
restarting playback. Refreshing For you applies the latest full ranking and
removals. The feed still returns up to eight personalized recommendations (five
in related-video mode); catalog polling does not turn this into an unlimited feed.
A database change may take about 20 seconds plus query time to reach an open feed
because the backend and browser check independently.

## Recommendation algorithm

`services/recommender.py` contains `VideoRecommender`, a pure ranking class. Its
constructor accepts records from the service, not a filename or database client.

1. Combine title, description, tags, and category into one text per video.
2. Use `TfidfVectorizer(stop_words='english')` to learn sparse TF-IDF vectors.
3. On recommendation requests, compare only selected/preference rows against
   the catalog using cosine similarity.
4. Calculate each candidate's score:

```text
score = mean similarity to liked videos
      - mean similarity to disliked videos
      + 2 × similarity to selected video (only in related-video mode)
```

5. Exclude disliked videos and the selected source video, then return the highest
   scores. Already-liked videos remain available for revisiting/changing feedback.
6. Cold-start and tied scores preserve graph popularity order.

Unknown preference IDs are ignored. Empty catalogs return an empty list. Empty
vocabularies use zero scores and preserve catalog order. No dense all-pairs
N × N similarity matrix is created. The matrix is still in application memory;
there is no graph vector index, neural embedding, or collaborative filtering.
Keyword overlap can miss synonyms. The whole catalog is loaded, so pagination
and a larger-scale retrieval strategy would be needed for very large catalogs.

## API contract

| Method and route | Behavior |
| --- | --- |
| `POST /api/auth/login` | Verify credentials, persist profile, issue bearer token. |
| `GET /api/auth/me` | Return verified identity and expiry. |
| `GET /api/videos` | Return up to eight personalized graph videos. |
| `GET /api/videos?video_id=...` | Return up to five related videos with user preferences applied. |
| `POST /api/videos/reaction` | Save `like`, `dislike`, or `none` for a graph video. |
| `GET /api/health` | Process liveness. |

Protected requests require `Authorization: Bearer <token>`.

```json
{"video_id": "abc123", "reaction": "like"}
```

The reaction response returns `video_id` and the saved `reaction` (`null` for
neutral). Feed entries include a per-user `reaction` field. Saving feedback does
not reorder the visible cards immediately, allowing undo. The next feed load or
Find similar request uses the new preference; disliked videos then disappear.

Status codes: 401 for authentication failures, 404 for missing videos/profiles,
422 for validation, 429 for login rate limits, and 503 for caught Neo4j/driver/OS
errors. The common database error handler hides connection details. Middleware
adds `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

## Database access

`core/database.py` owns sessions and parameterized read/write transactions.
Each operation closes its session and driver. Connection timeout is five seconds
and automatic retries are disabled; this is not a total request deadline.
Windows uses the system certificate store through truststore with TLS
verification enabled. There are no database credentials in frontend code.

## Run and validate

From the repository root using the existing root environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend --host 127.0.0.1 --port 8000
```

Interactive API docs: `http://127.0.0.1:8000/docs`.

Run tests from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q
```

Tests inject an in-memory repository or mock database methods. They cover auth,
user isolation, reaction replacement/removal, preference ranking, string IDs,
empty data, cache refresh, and failure responses without requiring live Aura.
`inspect_neo4j.py` remains a separate read-only schema inspection utility.
