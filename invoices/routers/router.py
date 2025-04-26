from fastapi import APIRouter
from clients.zoho_client import ZohoEmailAPI
from middlewares.verify_token_route import VerifyTokenRoute


router = APIRouter(
    prefix="/v1/invoices",
    tags=["invoices"],
    route_class=VerifyTokenRoute,
)


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
    
