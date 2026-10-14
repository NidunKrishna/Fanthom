"""Assemble API routes, graph persistence, recommendation services, and errors."""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError, DriverError
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import LoginLimiter, router
from .api.videos import router as videos_router
from .core.database import GraphDatabaseClient
from .repositories.graph import GraphRepository
from .services.feed import FeedService
from .core.config import Settings
from .core.security import password_hasher


def create_app(settings: Settings | None = None, repository=None) -> FastAPI:
    """Build an app; allow repository injection for isolated, network-free tests."""
    settings = settings or Settings()
    @asynccontextmanager
    async def lifespan(app):
        """Poll Neo4j while the API runs and stop polling during shutdown."""
        app.state.feed.start()
        try:
            yield
        finally:
            await asyncio.to_thread(app.state.feed.stop)

    app = FastAPI(title="Aphrodite.ai", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.password_hash = settings.password_hash or password_hasher.hash(settings.password)
    app.state.limiter = LoginLimiter()
    app.state.repository = repository if repository is not None else GraphRepository(GraphDatabaseClient(settings))
    app.state.feed = FeedService(app.state.repository, settings.catalog_poll_seconds)
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins,
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
    app.include_router(router)
    app.include_router(videos_router)

    async def database_unavailable(request, error):
        """Hide driver/credential details and provide a retryable HTTP response."""
        return JSONResponse(status_code=503, content={'detail': 'The video database is temporarily unavailable. Please try again.'}, headers={'Cache-Control': 'no-store'})

    for error_type in (Neo4jError, DriverError, OSError):
        app.add_exception_handler(error_type, database_unavailable)

    @app.middleware("http")
    async def security_headers(request, call_next):
        """Disable response caching and MIME-type guessing."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health", tags=["Health"])
    def health():
        """Report process liveness; this does not query the graph."""
        return {"status": "ok"}

    return app


app = create_app()
