from fastapi import HTTPException, status
from clients.zoho_client import ZohoEmailClient
from models.models import Subscriptions

zoho_client = ZohoEmailClient()
zoho_client.connect()


def _send_credentials(
        email: str,
        password: str,
        is_company: bool = False
) -> None:
    """
    Send credentials to the user.
    """

    try:
        if not email or not password:
            raise ValueError("Email and hashed password cannot be empty.")

        # Prepare the email content
        content = (
            f"""Your credentials are:
            Username: {email}
            Password: {password}"""
        )

        if is_company:
            content = f"Your API key is: {password}"

        # Send email using Zoho API
        zoho_client.send_email(
            to_address=email,
            subject="Welcome to Control Tax!",
            content=content
        )

    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send credentials. {e}",
        ) from e


def _get_subscription_by_name(
    subscription_name: str,
    db,
) -> Subscriptions:
    """
    Get subscription by name.
    """
    try:
        subscription = (
            db.query(Subscriptions)
            .filter(Subscriptions.name == subscription_name)
            .first()
        )
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found.",
            )
        return subscription
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the subscription. {e}",
        ) from e
