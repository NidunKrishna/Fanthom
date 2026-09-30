from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import LoginLimiter, router
from .core.config import Settings
from .core.security import password_hasher


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Aphrodite.ai", version="1.0.0")
    app.state.settings = settings
    app.state.password_hash = settings.password_hash or password_hasher.hash(settings.password)
    app.state.limiter = LoginLimiter()
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins,
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
    app.include_router(router)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
