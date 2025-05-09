from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class IssuerSchema(BaseModel):
    id: UUID
    nit: str
    name: str
    commercial_name: Optional[str] = None
    address: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True

class RecipientSchema(BaseModel):
    id: UUID
    nit: str
    name: str
    email: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True

class ItemSchema(BaseModel):
    id: UUID  # Change to UUID if your items also use UUIDs for IDs
    description: str
    quantity: float
    unit_price: float
    total: float
    total: float

    class Config:
        from_attributes = True

class InvoiceSchema(BaseModel):
    id: UUID
    authorization_number: str
    series: str
    number: str
    document_type: str
    total: float
    vat: float
    currency: str
    emission_date: datetime
    xml_url: str
    issuer: IssuerSchema
    recipient: RecipientSchema
    items: List[ItemSchema] = []

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    status: str
    company_name: str
    company_nit: str
    invoices_count: int
    invoices: List[InvoiceSchema]