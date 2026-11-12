"""Pydantic request/response schemas.

Phase 1 includes only the minimal schemas needed for the health check and
authentication surface. Invoice/PayPal schemas are added in later phases.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "invoice-collection-agent"
    environment: str
    database_configured: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user: UserRead
    token: TokenResponse
