from fastapi import APIRouter
from app.clients.zoho_client import ZohoEmailAPI


router = APIRouter(prefix="/v1/invoices", tags=["invoices"])

emailProcessor = ZohoEmailAPI()


@router.get("/unread")
async def get_unread_emails():
    """Get unread emails"""
    
    emailProcessor.connect()
    emails = emailProcessor.get_unread_messages()
    return emails


@router.get("/test-zoho")
def test_zoho():
    # Instantiate your ZohoEmailAPI client.
    zoho_api = ZohoEmailAPI()
    try:
        zoho_api.connect()
        return {"status": "success", "access_token": zoho_api.access_token}
    except Exception as e:
        return {"status": "error", "error": str(e)}
