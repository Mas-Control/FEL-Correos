from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional
from datetime import datetime


class CompanyBase(BaseModel):
    """
    Base schema for Companies, shared across different operations.
    """
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_active: Optional[bool] = False


class CompanyCreate(CompanyBase):
    """
    Schema for creating a new Company.
    """
    email: EmailStr
    name: str
    nit: str
    accountant_email: Optional[EmailStr] = None


class CompanyUpdate(CompanyBase):
    """
    Schema for updating an existing Company.
    """
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyRead(CompanyBase):
    """
    Schema for reading Company data.
    """
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    api_key: Optional[str] = None

    class Config:
        form_attributes = True
