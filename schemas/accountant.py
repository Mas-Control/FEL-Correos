from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional
from datetime import datetime


class AccountantBase(BaseModel):
    """
    Base schema for Accountants, shared across different operations.
    """
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = False


class AccountantCreate(AccountantBase):
    """
    Schema for creating a new Accountant.
    """
    email: EmailStr
    password: Optional[str] = None
    subscription_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class AccountantUpdate(BaseModel):
    """
    Schema for updating an existing Accountant.
    """
    password: Optional[str] = None
    subscription_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None


class AccountantRead(AccountantBase):
    """
    Schema for reading Accountant data.
    """
    id: UUID
    subscription_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        form_attributes = True