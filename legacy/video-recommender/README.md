# VidRec — Sample Video Recommender App with Google SSO

A small Flask demo application that shows how to:

- Implement **Google Single Sign-On (SSO)** using OAuth2 / OpenID Connect (via [Authlib](https://docs.authlib.org/)).
- Build a simple **content-based recommender system** (TF-IDF + cosine similarity) using pandas/scikit-learn.
- Persist users and their watch/like history in SQLite via SQLAlchemy.
- Serve personalized recommendations that improve as a signed-in user watches/likes videos.

## Features

- 🔐 "Sign in with Google" button — no passwords, standard OAuth2 flow.
- 🎥 Sample catalog of 15 videos across categories (Education, Music, Cooking, Documentary).
- 🤖 Recommendations:
  - Not logged in → trending videos (cold start).
  - Logged in → personalized recommendations based on watch/like history.
  - Video detail page → "similar videos" based on that single video's content.
- 🔍 Simple keyword search.
- 👤 Profile page showing a user's watch/like history.

## Project structure

```text
video-recommender-app/
|-- app.py                    # Development entry point
|-- vidrec/
|   |-- __init__.py           # Application factory and startup wiring
|   |-- config.py             # Environment and application configuration
|   |-- extensions.py         # Shared SQLAlchemy instance
|   |-- models.py             # User and Interaction database models
|   |-- auth.py               # Shared session and template helpers
|   |-- routes/
|   |   |-- auth.py           # Google login, callback, and logout
|   |   |-- videos.py         # Home, video detail, likes, and search
|   |   `-- profile.py        # User profile and activity history
|   |-- services/
|   |   `-- recommender.py    # TF-IDF recommendation engine
|   |-- templates/            # Jinja2 templates
|   `-- static/style.css      # Application styles
|-- data/videos.csv           # Sample video catalog
|-- instance/app.db           # Local SQLite database (not committed)
|-- tests/                    # Route and application wiring checks
|-- requirements.txt
`-- .env.example              # Environment configuration template
```

The `vidrec.create_app()` factory initializes extensions and registers route
blueprints. Database and catalog paths resolve from the project directory,
so launching from another working directory uses the same data.


## 1. Setup

```bash
cd video-recommender-app
python -m venv venv
source venv/bin/activate    # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Create Google OAuth credentials

1. Go to the [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Create a project (or select an existing one).
3. Click **Create Credentials → OAuth client ID**.
4. Application type: **Web application**.
5. Add an **Authorized redirect URI**:
   ```
   http://localhost:5000/auth/callback
   ```
6. Copy the generated **Client ID** and **Client Secret** into your `.env` file:
   ```
   GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxxxxxx
   FLASK_SECRET_KEY=some-long-random-string
   ```
7. If prompted, configure the **OAuth consent screen** (External, add your Google account as a test user while in "Testing" mode).

## 3. Run the app

```bash
python app.py
```

Visit **http://localhost:5000**, click **"Sign in with Google"**, and you're in.

## 4. How the recommender works

- Each video has `title`, `tags`, `category`, `description`.
- `TfidfVectorizer` turns `title + tags + category` into vectors.
- `cosine_similarity` computes a similarity matrix between all videos.
- **Cold start** (no history): show trending/sample videos.
- **Personalized**: average the similarity rows of all videos a user liked/watched, rank all other videos by that averaged score.
- **"Similar to this video"**: look up that video's row in the similarity matrix directly.

This is intentionally simple (no collaborative filtering, no embeddings/ANN index) so it's easy to read and extend — e.g. swap in a real embeddings model, add collaborative filtering signals, or move the catalog to a real database.

## 5. Extending this sample

- Swap SQLite for Postgres/MySQL by changing `SQLALCHEMY_DATABASE_URI`.
- Add more OAuth providers (GitHub, Microsoft) via additional `oauth.register(...)` calls in `vidrec/__init__.py`.
- Replace the TF-IDF recommender with embeddings (e.g. sentence-transformers) + a vector DB for scale.
- Add pagination, ratings, watch progress, etc.

## Security notes (for production use)

- Never commit real `.env` values / secrets.
- Use HTTPS in production; Google OAuth redirect URIs must use `https://` outside of localhost.
- Rotate `FLASK_SECRET_KEY` and store secrets in a proper secret manager (not `.env`) in production.
- Add CSRF protection (e.g. `Flask-WTF`) for the like/form POST endpoints.

## Running checks

```bash
python -m unittest discover -s tests -v
```

Checks use an in-memory SQLite database and mock Google OAuth responses.
