from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class IssuerSchema(BaseModel):
    id: UUID
    nit: str
    name: str
    commercial_name: Optional[str] = None
    establishment_code: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    municipality: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecipientSchema(BaseModel):
    id: UUID
    nit: str
    name: str
    email: Optional[str] = None

    class Config:
        from_attributes = True

class ItemSchema(BaseModel):
    id: UUID
    invoice_id: UUID
    line_number: int
    good_or_service: str
    quantity: float
    unit_of_measure: str
    description: str
    unit_price: float
    price: float
    discount: float
    total: float
    taxes: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

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