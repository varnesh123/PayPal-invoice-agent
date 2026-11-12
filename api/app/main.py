"""FastAPI application entry point.

Phase 1 (Foundation): provides a health-check endpoint and the route
structure used by later phases (PayPal, AI agent, invoices, webhooks).

Endpoints:
    GET /health  — backend health check (returns 200 when running)
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_settings, get_supabase
from app.schemas import HealthResponse
from app.auth import get_current_user


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Invoice Collection Agent — backend (FastAPI)",
        version="0.1.0",
        debug=settings.debug,
    )

    # --- CORS ---------------------------------------------------------------
    # Allow the Next.js frontend (localhost:3000 in development) to call
    # the backend. Tighten allowed origins before production deployment.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes -------------------------------------------------------------
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health(request: Request):
        """Health-check endpoint.

        Returns 200 when the backend is running. Reports whether the
        Supabase database client is configured (not whether it is reachable,
        since Supabase may not be provisioned yet in Phase 1).
        """
        supabase = get_supabase()
        return HealthResponse(
            environment=settings.app_env,
            database_configured=supabase is not None,
        )

    @app.get("/", tags=["root"])
    async def root():
        return {
            "service": settings.app_name,
            "status": "running",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
