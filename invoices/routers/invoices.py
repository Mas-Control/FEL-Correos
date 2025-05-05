from fastapi import APIRouter
from clients.zoho_client import ZohoEmailAPI
from middlewares.verify_token_route import VerifyTokenRoute
from fastapi import Request, HTTPException, Depends
from core.security import get_api_key


router = APIRouter(
    prefix="/v1/invoices",
    tags=["invoices"],
)


emailProcessor = ZohoEmailAPI()


@router.get("/unread")
async def get_unread_emails(api_key: str = Depends(get_api_key)):
    """Get unread emails"""

    emailProcessor.connect()
    emails = emailProcessor.get_unread_messages()
    return emails

    
@router.get("/test-zoho")
async def test_zoho(api_key: str = Depends(get_api_key)):
    """Test Zoho connection with API key authentication"""
    # Instantiate your ZohoEmailAPI client
    zoho_api = ZohoEmailAPI()
    try:
        # The request has been authenticated with API key
        zoho_api.connect()
        return {"status": "success", "access_token": zoho_api.access_token}
    except Exception as e:
        return {"status": "error", "error": str(e)}

