"""Invoices router for handling invoice-related operations."""

from uuid import UUID
from fastapi import APIRouter
from clients.zoho_client import ZohoEmailClient
from fastapi import Depends, Header
from core.security import get_api_key, verify_api_key
from core.services.xml.xml_job import download_parse_delete
from logging import getLogger
from sqlalchemy.orm import Session
from database import get_db
from models.models import Companies
from models.models import Invoices
from fastapi import HTTPException, status
from schemas.invoices import InvoiceListResponse, InvoiceSchema

logger = getLogger(__name__)

router = APIRouter(prefix="/v1/invoices", tags=["invoices"])

zoho_client = ZohoEmailClient()
zoho_client.connect()


@router.get("/process")
async def process_invoices(
    api_key: str = Depends(get_api_key), db: Session = Depends(get_db)
):
    """Get unread emails"""
    try:
        logger.info("Fetching unread emails from Zoho")
        emails = zoho_client.get_unread_messages()
        if not emails:
            logger.info("No unread emails found")
            return []
        logger.info("Found %s unread emails", len(emails))
        xml_errors: list[dict] = []

        for email in emails:
            message_id = email["messageId"]
            logger.info("Processing email with message ID: %s", message_id)

            html_content = zoho_client.get_email_content(message_id)
            if not html_content:
                logger.warning(
                    "Failed to fetch email content, message ID: %s", message_id
                )

                xml_errors.append(
                    {
                        "messageId": message_id,
                        "error": "Failed to fetch content",
                    }
                )
                continue
            logger.info("Extracting XML link from email content")
            xml_url = zoho_client.extract_xml_link(html_content)
            if not xml_url:
                logger.warning("No XML link found, message ID: %s", message_id)
                xml_errors.append(
                    {"messageId": message_id, "error": "No XML link found"}
                )
                continue

            await download_parse_delete(xml_url, db)

            logger.info("Marking email as read, message ID: %s", message_id)
            zoho_client.mark_messages_as_read(message_id)

    except Exception as e:
        print(f"Error fetching unread emails: {e}")
        raise e


@router.get("/test-zoho")
async def test_zoho(api_key: str = Depends(get_api_key)):
    """Test Zoho connection with API key authentication"""

    try:
        return {"status": "success", "access_token": zoho_client.access_token}
    except HTTPException as e:
        return {"status": "error", "error": str(e)}


@router.get("/company-invoices", response_model=InvoiceListResponse)
async def get_company_invoices(
    api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
    invoice_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """Get invoices with filters for a company based on API key
    Args:
        api_key (str, optional): API key for authorization. Defaults to Header(..., alias="X-API-Key").
        db (Session, optional): Database session. Defaults to Depends(get_db).
        invoice_id (int, optional): Filter by invoice ID. Defaults to None.
        status_code (str, optional): Filter by status code. Defaults to None.
        date_from (str, optional): Filter by creation date from. Defaults to None.
        date_to (str, optional): Filter by creation date to. Defaults to None.
    Raises:
        HTTPException: 401 if the API key is invalid.
        HTTPException: 500 if there is a server error.
    Returns:
        dict: A dictionary containing the status, company name, company NIT, invoices count, and a list of invoices.
    """
    try:
        # Get the company from the database using the API key as authorization
        # code

        companies = db.query(Companies).all()

        # Find the matching company using hashed key verification
        company = next(
            (c for c in companies if verify_api_key(api_key, c.api_key)), None
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization code",
            )
        # Check if the company is active
        if not company.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active, please contact support",
            )

        # Get all invoices for the company, including relationships, with limit and offset
        query = db.query(Invoices).filter(Invoices.company_id == company.id)

        if invoice_id is not None:
            query = query.filter(Invoices.id == invoice_id)

        if date_from is not None:
            query = query.filter(Invoices.emission_date >= date_from)

        if date_to is not None:
            query = query.filter(Invoices.emission_date <= date_to)

        invoices = query.all()

        # Serialize invoices using the Pydantic schema
        invoices_data = [InvoiceSchema.from_orm(inv) for inv in invoices]

        # Prepare response with full data
        return {
            "status": "success",
            "company_name": company.name,
            "company_nit": company.nit,
            "invoices_count": len(invoices),
            "invoices": invoices_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching company invoices: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve invoices: {str(e)}",
        ) from e


@router.get("/company-invoice-count", response_model=dict)
async def get_company_invoice_count(
    api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Get the count of invoices for a company based on API key"""
    try:
        # Get the company from the database using the API key
        companies = db.query(Companies).all()

        # Find the matching company using hashed key verification
        company = next(
            (c for c in companies if verify_api_key(api_key, c.api_key)), None
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization code",
            )

        # Count the number of invoices for the company
        invoice_count = (
            db.query(Invoices).filter(Invoices.company_id == company.id).count()
        )

        return {
            "status": "success",
            "company_name": company.name,
            "company_nit": company.nit,
            "invoice_count": invoice_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching invoice count: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve invoice count: {str(e)}",
        ) from e
