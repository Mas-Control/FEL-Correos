"""
Zoho Email API client.

This class is responsible for connecting to the Zoho Email API.
"""

from datetime import datetime, timedelta
import logging
import requests
from app.config import get_settings
from typing import Dict, List

logger = logging.getLogger(__name__)


class ZohoEmailAPI:
    """
    Zoho Email API client.

    This class is responsible for connecting to the Zoho Email API.
    """
    def __init__(self) -> None:
        settings = get_settings()
        self.client_id = settings.ZOHO_CLIENT_ID
        self.client_secret = settings.ZOHO_CLIENT_SECRET
        self.access_token = settings.ZOHO_ACCESS_TOKEN
        self.refresh_token = settings.ZOHO_REFRESH_TOKEN
        self.api_domain = settings.ZOHO_API_DOMAIN
        self.account_id = settings.ZOHO_ACCOUNT_ID
        self.folder_id = settings.ZOHO_FOLDER_ID
        # For testing, force token refresh immediately
        self.token_expiry = datetime.now() - timedelta(seconds=1)

    def refresh_access_token(self) -> str:
        """
        Refresh the access token using the refresh token.
        According to the documentation, we need to make a POST request to:

        {Accounts_URL}/oauth/v2/token?refresh_token={refresh_token}&
        client_id={client_id}&client_secret={client_secret}&grant_type=refresh_token

        If successful, the response will contain the new access token.
        """
        try:
            token_url = "https://accounts.zoho.com/oauth/v2/token"

            params = {
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
            }
            response = requests.post(token_url, params=params, timeout=50)
            if response.status_code != 200:
                logger.error(
                    "Failed to refresh access token: %s", response.text
                )
                raise requests.exceptions.RequestException(
                    "Failed to refresh access token"
                )

            token_data = response.json()
            self.access_token = token_data.get("access_token")

            expires_in = int(token_data.get("expires_in", 3600))
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            return self.access_token

        except Exception as e:
            logger.error("Failed to refresh access token: %s", str(e))
            raise

    def connect(self) -> None:
        """
        Ensure that a valid access token is available.
        If the token is expired, refresh it.
        """
        try:
            if datetime.now() >= self.token_expiry:
                self.refresh_access_token()
            logger.info(
                "Connected to Zoho Mail API with a valid access token."
            )
        except Exception as e:
            logger.error("Failed to connect to Zoho Mail API: %s", str(e))
            raise
    
    def get_all_folders(self) -> List[Dict]:
        """
        Retrieves all folders from the Zoho account.
        Adjust the endpoint and parameters based on Zoho's API.
        """

        url = f"{self.api_domain}/{self.account_id}/folders"
        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
        response = requests.get(url, headers=headers, timeout=50)
        if response.status_code != 200:
            logger.error("Error fetching folders: %s", response.text)
            raise requests.exceptions.RequestException(
                "Error fetching folders from Zoho Mail API"
            )
        data = response.json()
        folders = data.get("data", [])
        return folders

    def get_unread_messages(self) -> List[Dict]:
        """
        Retrieves unread messages from the 'inbox' folder.
        Adjust the endpoint and parameters based on Zoho's API.
        """
        url = (
            f"{self.api_domain}/{self.account_id}/messages/view"
        )
        params = {
            "folderId": self.folder_id,
            "status": "unread",
        }
        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
        logger.info("Fetching unread messages from Zoho...")
        response = requests.get(
            url, headers=headers, params=params, timeout=50
        )
        if response.status_code != 200:
            logger.error("Error fetching messages: %s", response.text)
            raise requests.exceptions.RequestException(
                "Error fetching messages from Zoho Mail API"
            )
        data = response.json()
        # Adjust parsing based on the actual structure of the response.
        messages = data.get("data", [])
        logger.info("Fetched %d unread messages.", len(messages))
        return messages



