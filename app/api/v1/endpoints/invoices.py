from fastapi import APIRouter
from app.clients.zoho_client import ZohoEmailAPI


router = APIRouter(prefix="/v1/invoices", tags=["invoices"])

emailProcessor = ZohoEmailAPI()


@router.get("/unread")
async def get_unread_emails():
    """Get unread emails"""
    return {"message": "Get unread emails"}
