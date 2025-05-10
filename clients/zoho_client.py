"""
Zoho Email API client.

This class is responsible for connecting to the Zoho Email API.
"""

from datetime import datetime, timedelta
import logging
import re
from typing import Dict, List, Optional
import requests
from config import get_settings

logger = logging.getLogger(__name__)


class ZohoEmailClient:
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
        self.zoho_email = settings.ZOHO_EMAIL
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
                logger.error("Failed to refresh access token: %s", response.text)
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
            logger.info("Connected to Zoho Mail API with a valid access token.")
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
        url = f"{self.api_domain}/{self.account_id}/messages/view"
        params = {
            "folderId": self.folder_id,
            "status": "unread",
        }
        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
        logger.info("Fetching unread messages from Zoho...")
        response = requests.get(url, headers=headers, params=params, timeout=50)
        if response.status_code != 200:
            logger.error("Error fetching messages: %s", response.text)
            raise requests.exceptions.RequestException(
                "Error fetching messages from Zoho Mail API"
            )
        data = response.json()
        messages: list = data.get("data", [])
        logger.info("Fetched %d unread messages.", len(messages))
        return messages

    def get_email_content(self, message_id: str) -> str:
        """
        Retrieves the content of a specific email message.
        Adjust the endpoint and parameters based on Zoho's API.

        Args:
            message_id (str): The ID of the email message to retrieve.

            Returns:
            str: The HTML content of the email message.
        """
        try:
            self.connect()
            if datetime.now() >= self.token_expiry:
                self.refresh_access_token()

            # Zoho Mail API URL get content of an email
            base_url = f"{self.api_domain}/{self.account_id}/folders/"
            url = f"{base_url}{self.folder_id}/messages/{message_id}/content"

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Zoho-oauthtoken {self.access_token}",
            }

            response = requests.get(url, headers=headers, timeout=50)

            # Check if the response is successful
            if response.status_code != 200:
                logger.error("Error fetching email content: %s", response.text)
                raise requests.exceptions.RequestException(
                    "Error fetching email content from Zoho Mail API"
                )
            data = response.json()
            # Return the HTML content of the email
            email_content = data.get("data", {}).get("content", "")
            return email_content

        except Exception as e:
            logger.error("Failed to fetch email content: %s", str(e))
            raise

    def extract_xml_link(self, html_content: str) -> str:
        """
        Extracts the XML link from the HTML content of an email.
        Args:
            html_content (str): The HTML content of the email.

        Returns:
            str: The extracted XML link.
        """
        try:
            pattern = re.compile(
                (
                    r'<a\s+[^>]*href="(https://felav02\.c\.sat\.gob\.gt/[^"]*/'
                    r'descargaXml/[^"]+)"'
                ),
                re.IGNORECASE,
            )
            match = pattern.search(html_content)
            return match.group(1) if match else "No link found"
        except Exception as e:
            logger.error("Failed to extract XML link: %s", str(e))
            raise

    def mark_messages_as_read(self, message_ids: List[str]) -> None:
        """
        Marks the specified messages as read in the Zoho Mail API.
        Args:
            message_ids (List[str]): List of message IDs to mark as read.
        """
        url = f"{self.api_domain}/{self.account_id}/updatemessage"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
        }
        payload = {"mode": "markAsRead", "messageId": message_ids}
        try:
            response = requests.put(url, headers=headers, json=payload, timeout=50)
            if response.status_code != 200:
                logger.error("Error marking messages as read: %s", response.text)
                raise requests.exceptions.RequestException(
                    "Error marking messages as read"
                )
            logger.info("Successfully marked messages as read.")
        except Exception as e:
            logger.error("Failed to mark messages as read: %s", str(e))

    def send_email(
        self,
        to_address: str,
        subject: str,
        content: str,
        cc_address: Optional[str] = None,
    ) -> Dict:
        """
        Sends an email using the Zoho Mail API.
        """
        self.connect()

        url = f"{self.api_domain}/{self.account_id}/messages"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
        }

        payload = {
            "fromAddress": self.zoho_email,
            "toAddress": to_address,
            "ccAddress": cc_address if cc_address else "",
            "subject": subject,
            "content": content,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=50)
            if response.status_code != 200:
                logger.error("Failed to send email: %s", response.text)
                raise requests.exceptions.RequestException("Failed to send email")
            logger.info("Email sent successfully.")
            return response.json()
        except Exception as e:
            logger.error("Exception during email sending: %s", str(e))
            raise
