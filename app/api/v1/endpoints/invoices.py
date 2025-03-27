from fastapi import APIRouter
from app.clients.zoho_client import ZohoEmailAPI


router = APIRouter(prefix="/v1/invoices", tags=["invoices"])

emailProcessor = ZohoEmailAPI()
emailProcessor.connect()


@router.get("/unread")
async def get_unread_emails():
    """Get unread emails"""
    
    emails = emailProcessor.get_unread_messages()
    return emails
