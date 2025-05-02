"""
Pydantic schemas for the application.

This module defines the schemas used for input validation and serialization.
"""

from typing import Optional
from pydantic import BaseModel


class TokenBase(BaseModel):
    """
    Base schema for a token.

    Attributes:
        access_token (str): The actual token string used for authentication.
        token_type (str): The type of the token (e.g., 'bearer').
    """

    access_token: str
    expires_in: int
    token_type: str


class TokenCreate(TokenBase):
    """
    Schema for creating a new token.

    This schema is used for creating tokens, inheriting common fields from
    TokenBase. No additional fields are needed beyond those in TokenBase.
    """


class Token(TokenBase):
    """
    Schema representing a token, including additional fields if needed.

    Inherits from TokenBase and adds:
    - refresh_token (Optional[str]): An optional refresh token used to obtain
    new access tokens.
    """

    refresh_token: Optional[str] = None

    class Config:  # pylint: disable=too-few-public-methods
        """
        Pydantic configuration class.

        - from_attributes (bool): Enables compatibility with SQLAlchemy models.
        """

        from_attributes = True
