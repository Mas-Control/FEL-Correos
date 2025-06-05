"""
SQLAlchemy models for the application.
"""

# pylint: disable=too-few-public-methods
from sqlalchemy import (
    Integer,
    String,
    Float,
    ForeignKey,
    func,
    Boolean,
    DateTime,
    JSON,
)
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as standardUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from database import Base


class Issuer(Base):
    """
    Represents the 'Issuer' entity in the system.
    The Issuer is responsible for issuing invoices and includes details such
    as NIT, name, and commercial information.
    """

    __tablename__ = "issuers"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    nit: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    commercial_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    establishment_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-many relationship: one issuer can have many invoices
    invoices: Mapped[List["Invoices"]] = relationship(
        "Invoices", back_populates="issuer"
    )


class Recipient(Base):
    """
    Represents the 'Recipient' entity in the system.
    The Recipient is the entity receiving the invoice, including details such
    as NIT, name, and address.
    """

    __tablename__ = "recipients"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    nit: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-many relationship: one recipient can have many invoices
    invoices: Mapped[List["Invoices"]] = relationship(
        "Invoices", back_populates="recipient"
    )


class Invoices(Base):
    """
    Represents the 'Invoices' entity in the system.
    An invoice includes details like the authorization number, issue date,
    total, tax (IVA), associated issuer, and recipient.
    """

    __tablename__ = "invoices"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    company_id: Mapped[standardUUID] = mapped_column(
        UUID, ForeignKey("companies.id"), nullable=False, index=True
    )
    authorization_number: Mapped[str] = mapped_column(String)
    series: Mapped[str] = mapped_column(String)
    number: Mapped[str] = mapped_column(String)
    document_type: Mapped[str] = mapped_column(String)
    issuer_id: Mapped[standardUUID] = mapped_column(UUID, ForeignKey("issuers.id"))
    recipient_id: Mapped[standardUUID] = mapped_column(
        UUID, ForeignKey("recipients.id")
    )
    total: Mapped[float] = mapped_column(Float)
    vat: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="GTQ")
    xml_url: Mapped[str] = mapped_column(String)

    # pylint: disable=not-callable
    emission_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processing_date: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-many relationship: one invoice can have many items
    items: Mapped[List["Item"]] = relationship("Item", back_populates="invoice")

    # One-to-one relationship: one invoice belongs to one company
    company: Mapped["Companies"] = relationship("Companies", back_populates="invoices")

    # One-to-one relationship: one invoice belongs to one issuer
    issuer: Mapped["Issuer"] = relationship("Issuer", back_populates="invoices")
    # One-to-one relationship: one invoice belongs to one recipient
    recipient: Mapped["Recipient"] = relationship(
        "Recipient", back_populates="invoices"
    )


class Item(Base):
    """
    Represents the 'Item' entity within an invoice.
    An item is a line entry in an invoice, detailing the quantity, description,
    price, and associated taxes.
    """

    __tablename__ = "items"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    invoice_id: Mapped[standardUUID] = mapped_column(UUID, ForeignKey("invoices.id"))
    line_number: Mapped[int] = mapped_column(Integer)
    good_or_service: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float)
    unit_of_measure: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    unit_price: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    discount: Mapped[float] = mapped_column(Float)
    total: Mapped[float] = mapped_column(Float)
    taxes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-one relationship: one item belongs to one invoice
    invoice: Mapped["Invoices"] = relationship("Invoices", back_populates="items")


class InvoicesSummaries(Base):
    """
    Represents a summarized version of an invoice.
    The Invoices Summary includes key details like the authorization number,
    emission date, issuer details, and total amount.
    """

    __tablename__ = "invoices_summaries"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    client_summary_id: Mapped[standardUUID] = mapped_column(
        UUID, ForeignKey("client_summaries.id")
    )
    authorization_number: Mapped[str] = mapped_column(String)
    emission_date: Mapped[datetime] = mapped_column(DateTime)
    issuer_name: Mapped[str] = mapped_column(String)
    issuer_nit: Mapped[str] = mapped_column(String)
    total: Mapped[float] = mapped_column(Float)
    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-one relationship: one invoice summary belongs to one client
    # summary
    client_summary: Mapped["ClientsSummaries"] = relationship(
        "ClientsSummaries", back_populates="invoices"
    )


class ClientsSummaries(Base):
    """
    Represents a summary of a client's invoices.
    The Client Summary includes information about the client and an aggregated
    total of invoices issued to them.
    """

    __tablename__ = "client_summaries"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    nit: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    total_invoices: Mapped[int] = mapped_column(Integer)
    total_sum: Mapped[float] = mapped_column(Float)
    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # Bidirectional relationship with InvoicesSummaries
    invoices: Mapped[List["InvoicesSummaries"]] = relationship(
        "InvoicesSummaries", back_populates="client_summary"
    )


class Accountants(Base):
    """
    Represents the 'Accountants' entity in the system.
    The Accountants entity includes authentication details for an Accountants.
    """

    __tablename__ = "accountants"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    subscription_id: Mapped[standardUUID] = mapped_column(
        UUID, ForeignKey("subscriptions.id")
    )
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-one relationship: one accountant can have one subscription
    subscription: Mapped["Subscriptions"] = relationship(
        "Subscriptions", back_populates="accountants"
    )

    # One-to-many relationship: one accountant can have many companies
    accountant_companies: Mapped[List["AccountantCompanies"]] = relationship(
        "AccountantCompanies", back_populates="accountant"
    )
    invoice_requests: Mapped[List["InvoiceRequests"]] = relationship(
        "InvoiceRequests", back_populates="accountant"
    )


class Companies(Base):
    """
    Represents the 'Companies' entity in the system.
    The Companies entity includes details about the company, such as its
    name and address.
    """

    __tablename__ = "companies"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    nit: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    subscription_id: Mapped[Optional[standardUUID]] = mapped_column(
        UUID, ForeignKey("subscriptions.id"), nullable=True, default=None
    )
    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-many relationship: one company can have many invoices
    invoices: Mapped[List["Invoices"]] = relationship(
        "Invoices", back_populates="company"
    )
    # One-to-many relationship: one company can have many accountants
    accountant_companies: Mapped[List["AccountantCompanies"]] = relationship(
        "AccountantCompanies", back_populates="company"
    )
    invoice_requests: Mapped[List["InvoiceRequests"]] = relationship(
        "InvoiceRequests", back_populates="company"
    )
    # One-to-one relationship: one company can have one subscription
    subscription: Mapped["Subscriptions"] = relationship(
        "Subscriptions", back_populates="companies"
    )


class AccountantCompanies(Base):
    """
    Represents the 'AccountansCompanies' entity in the system.
    The AccountansCompanies entity includes details about the relationship
    between accountants and companies.
    """

    __tablename__ = "accountant_companies"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    accountant_id: Mapped[standardUUID] = mapped_column(
        UUID, ForeignKey("accountants.id")
    )
    company_id: Mapped[standardUUID] = mapped_column(UUID, ForeignKey("companies.id"))
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )
    # One-to-one relationship: one accountant belongs to one company
    accountant: Mapped["Accountants"] = relationship(
        "Accountants", back_populates="accountant_companies"
    )
    # One-to-one relationship: one company belongs to one accountant
    company: Mapped["Companies"] = relationship(
        "Companies", back_populates="accountant_companies"
    )


class Subscriptions(Base):
    """
    Represents the 'Subscription' entity in the system.
    The Subscription entity includes details about the subscription plan
    and its status.
    """

    __tablename__ = "subscriptions"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String, default="GTQ")
    invoices_limit: Mapped[int] = mapped_column(Integer, default=0)
    nit_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )

    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )
    # One-to-many relationship: one subscription can have many companies
    companies: Mapped[List["Companies"]] = relationship(
        "Companies", back_populates="subscription"
    )
    # One-to-many relationship: one subscription can have many accountants
    accountants: Mapped[List["Accountants"]] = relationship(
        "Accountants", back_populates="subscription"
    )


class InvoiceRequests(Base):
    """
    Represents the 'InvoiceRequests' entity in the system.
    Tracks the number of invoices requested by companies and accountants.
    """

    __tablename__ = "invoice_requests"

    id: Mapped[standardUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    company_id: Mapped[Optional[standardUUID]] = mapped_column(
        UUID, ForeignKey("companies.id"), nullable=True
    )
    accountant_id: Mapped[Optional[standardUUID]] = mapped_column(
        UUID, ForeignKey("accountants.id"), nullable=True
    )
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    last_request_date: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    # pylint: disable=not-callable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    company: Mapped[Optional["Companies"]] = relationship(
        "Companies", back_populates="invoice_requests"
    )
    accountant: Mapped[Optional["Accountants"]] = relationship(
        "Accountants", back_populates="invoice_requests"
    )
