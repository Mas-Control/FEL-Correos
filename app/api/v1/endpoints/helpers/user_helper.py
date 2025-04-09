from fastapi import HTTPException, status
from app.clients.zoho_client import ZohoEmailAPI

zoho_api = ZohoEmailAPI()


def _send_credentials(email: str, password: str) -> None:
    """
    Send credentials to the user.
    """
    try:
        zoho_api.connect()
        if not email or not password:
            raise ValueError("Email and hashed password cannot be empty.")

        zoho_api.send_email(
            to_address=email,
            subject="Welcome to Control Tax!",
            from_address='compartida@control.com.gt',
            content=(
                f"""Your credentials are:
                Username: {email}
                Password: {password}"""
            ),
        )

    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send credentials. {e}",
        ) from e
