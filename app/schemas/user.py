from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AuthBase(BaseModel):
    """
    Base schema for Auth entity.
    """
    issuer_id: int
    username: str
    is_active: bool
    role: str


class AuthCreate(AuthBase):
    """
    Schema for creating an Auth entity.
    """
    password: str = Field(..., min_length=8)


class AuthUpdate(BaseModel):
    """
    Schema for updating an Auth entity.
    """
    username: Optional[str]
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool]
    role: Optional[str]


class AuthResponse(AuthBase):
    """
    Schema for returning an Auth entity.
    """
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        form_attributes = True