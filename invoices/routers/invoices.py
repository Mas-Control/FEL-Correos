"""Invoices router for handling invoice-related operations."""
from fastapi import APIRouter
from clients.zoho_client import ZohoEmailClient
from fastapi import Depends
from core.security import get_api_key
from core.services.xml.xml_job import download_parse_delete
from logging import getLogger
from sqlalchemy.orm import Session
from database import get_db

logger = getLogger(__name__)

router = APIRouter(
    prefix="/v1/invoices",
    tags=["invoices"]
)

zoho_client = ZohoEmailClient()
zoho_client.connect()


@router.get("/process")
async def process_invoices(
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db)
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
                        "error": "Failed to fetch content"
                    }
                )
                continue
            logger.info("Extracting XML link from email content")
            xml_url = zoho_client.extract_xml_link(html_content)
            if not xml_url:
                logger.warning(
                    "No XML link found, message ID: %s", message_id
                )
                xml_errors.append(
                    {
                        "messageId": message_id,
                        "error": "No XML link found"
                    }
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
    except Exception as e:
        return {"status": "error", "error": str(e)}