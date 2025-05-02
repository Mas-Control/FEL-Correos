from sqlalchemy import (
    Integer, String, Float, DateTime, ForeignKey, Text, func, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
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

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    nit: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    commercial_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    establishment_code: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # pylint: disable=not-callable
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-many relationship: one issuer can have many invoices
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice", back_populates="issuer"
    )

    # One-to-one relationship: one issuer has one authentication
    auth: Mapped["Auth"] = relationship("Auth", back_populates="issuer")


class Recipient(Base):
    """
    Represents the 'Recipient' entity in the system.
    The Recipient is the entity receiving the invoice, including details such
    as NIT, name, and address.
    """
    __tablename__ = "recipients"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    nit: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # pylint: disable=not-callable
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # One-to-many relationship: one recipient can have many invoices
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice", back_populates="recipient"
    )


class Item(Base):
    """
    Represents the 'Item' entity within an invoice.
    An item is a line entry in an invoice, detailing the quantity, description,
    price, and associated taxes.
    """
    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    line_number: Mapped[int] = mapped_column(Integer)
    good_or_service: Mapped[str] = mapped_column(String)
    quantity: Mapped[Float] = mapped_column(Float)
    unit_of_measure: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    unit_price: Mapped[Float] = mapped_column(Float)
    price: Mapped[Float] = mapped_column(Float)
    discount: Mapped[Float] = mapped_column(Float)
    total: Mapped[Float] = mapped_column(Float)
    taxes: Mapped[Optional[str]] = mapped_column(Text)

    # pylint: disable=not-callable
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # Foreign Key to Invoice
    invoice_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("invoices.id"))

    # Relationship to Invoice
    invoice: Mapped["Invoice"] = relationship(
        "Invoice", back_populates="items"
    )


class Invoice(Base):
    """
    Represents the 'Invoice' entity in the system.
    An invoice includes details like the authorization number, issue date,
    total, tax (IVA), associated issuer, and recipient.
    """
    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    authorization_number: Mapped[str] = mapped_column(String)
    series: Mapped[str] = mapped_column(String)
    number: Mapped[str] = mapped_column(String)
    document_type: Mapped[str] = mapped_column(String)
    issuer_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("issuers.id"))
    recipient_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("recipients.id")
    )
    total: Mapped[Float] = mapped_column(Float)
    vat: Mapped[Float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="GTQ")
    xml_path: Mapped[str] = mapped_column(String)
    certifier_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    certifier_nit: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # pylint: disable=not-callable
    emission_date: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now()
    )
    processing_date: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now()
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=True,
        server_default=func.now(),
        onupdate=func.now()
    )

    issuer: Mapped["Issuer"] = relationship(
        "Issuer", back_populates="invoices"
    )
    recipient: Mapped["Recipient"] = relationship(
        "Recipient", back_populates="invoices"
    )
    items: Mapped[List["Item"]] = relationship(
        "Item", back_populates="invoice"
    )


class InvoiceSummary(Base):
    """
    Represents a summarized version of an invoice.
    The Invoice Summary includes key details like the authorization number,
    emission date, issuer details, and total amount.
    """
    __tablename__ = "invoice_summaries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    client_summary_id: Mapped[UUID] = mapped_column(
        UUID, ForeignKey("client_summaries.id")
    )
    authorization_number: Mapped[str] = mapped_column(String)
    emission_date: Mapped[DateTime] = mapped_column(DateTime)
    issuer_name: Mapped[str] = mapped_column(String)
    issuer_nit: Mapped[str] = mapped_column(String)
    total: Mapped[Float] = mapped_column(Float)
    # pylint: disable=not-callable
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # Bidirectional relationship with ClientSummary
    client_summary: Mapped["ClientSummary"] = relationship(
        "ClientSummary", back_populates="invoices"
    )


class ClientSummary(Base):
    """
    Represents a summary of a client's invoices.
    The Client Summary includes information about the client and an aggregated
    total of invoices issued to them.
    """
    __tablename__ = "client_summaries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    nit: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    total_invoices: Mapped[int] = mapped_column(Integer)
    total_sum: Mapped[Float] = mapped_column(Float)
    # pylint: disable=not-callable
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # Bidirectional relationship with InvoiceSummary
    invoices: Mapped[List["InvoiceSummary"]] = relationship(
        "InvoiceSummary", back_populates="client_summary"
    )


class Auth(Base):
    """
    Represents the 'Auth' entity in the system.
    The Auth entity includes authentication details for an issuer.
    """
    __tablename__ = "auth"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    issuer_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("issuers.id"))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String)
    # pylint: disable=not-callable
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=True, server_default=func.now(), onupdate=func.now()
    )

    issuer: Mapped["Issuer"] = relationship("Issuer", back_populates="auth")
