from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth
from app.config import settings


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory (rather than a module-level `app = FastAPI()`) so tests can
    construct a fresh, independently-configured app when they need one.
    """
    app = FastAPI(title="Attaché API", version="0.1.0")

    # The browser sends the session cookie from a different origin
    # (localhost:3000 -> localhost:8000), so the API must name that origin
    # explicitly and allow credentials. "*" is not permitted with cookies.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Unauthenticated liveness probe — used by App Runner in M8."""
        return {"status": "ok"}

    return app


app = create_app()
