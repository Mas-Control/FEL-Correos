from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IssuerBase(BaseModel):
    """
    Shared properties for the Issuer schema.
    """
    nit: str
    name: str
    commercial_name: Optional[str] = None
    establishment_code: Optional[str] = None
    address: Optional[str] = None


class IssuerCreate(IssuerBase):
    """
    Properties required to create a new Issuer.
    """
    pass


class IssuerUpdate(IssuerBase):
    """
    Properties that can be updated for an Issuer.
    """
    pass


class IssuerInDBBase(IssuerBase):
    """
    Properties shared by models stored in the database.
    """
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        form_attributes = True


class Issuer(IssuerInDBBase):
    """
    Properties to return to the client.
    """
    pass


class IssuerInDB(IssuerInDBBase):
    """
    Properties stored in the database.
    """
    pass