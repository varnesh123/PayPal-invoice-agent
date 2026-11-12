"""Authentication helpers (Phase 1 scaffold).

Owner login/session for the dashboard only — this is separate from
PayPal OAuth (which is added in Phase 2).

At this stage the module defines the shape of authentication so the
backend can start and routes can be registered. Full session validation
against the database is wired up once Supabase is provisioned
(see migrations/0001_initial.sql).
"""

from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db import get_settings
from app.schemas import UserRead

# Bearer token scheme used by the Authorization header.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[UserRead]:
    """Return the authenticated owner, or None if not authenticated.

    Phase 1 returns None (open access) because there is no user database
    yet. In Phase 1 the health endpoint and frontend shell do not require
    auth. Auth enforcement is added once the `users` table exists and a
    session strategy (cookie/session or JWT) is selected.
    """
    # Intentional no-op in Phase 1. Auth is gated behind DB provisioning.
    return None


def require_auth(user: Optional[UserRead]) -> UserRead:
    """Dependency helper that enforces authentication once implemented."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication is not yet implemented (Phase 1 scaffold).",
    )
