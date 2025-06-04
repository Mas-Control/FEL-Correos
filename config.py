from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from functools import lru_cache

load_dotenv()


class Settings(BaseSettings):
    """
    Application settings.
    """

    # Zoho API Configuration
    ZOHO_CLIENT_ID: str
    ZOHO_CLIENT_SECRET: str
    ZOHO_ACCESS_TOKEN: str
    ZOHO_REFRESH_TOKEN: str
    ZOHO_API_DOMAIN: str
    ZOHO_ACCOUNT_ID: str
    ZOHO_FOLDER_ID: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    API_KEY: str
    REFRESH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 4320
    ALGORITHM: str
    JWT_SECRET: str
    ZOHO_EMAIL: str

    # Database Configuration
    DATABASE_URL: str

    class Config:
        """
        Configuration for the BaseSettings class.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def validate_settings(self):
        """
        Perform basic validation of critical settings.
        Raises ValueError if critical settings are missing.
        """
        required_fields = [
            "ZOHO_CLIENT_ID",
            "ZOHO_CLIENT_SECRET",
            "ZOHO_API_DOMAIN",
            "DATABASE_URL",
            "ZOHO_ACCOUNT_ID",
            "ZOHO_FOLDER_ID",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "REFRESH_ACCESS_TOKEN_EXPIRE_MINUTES",
            "ALGORITHM",
            "JWT_SECRET",
            "API_KEY",
            "ZOHO_EMAIL",
        ]
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Missing required configuration: {field}")


@lru_cache()
def get_settings() -> Settings:
    """
    Retrieve and validate application settings.

    Returns:
        Settings: Validated application settings.

    Raises:
        ValueError: If critical settings are missing.
    """
    try:
        settings = Settings()  # type: ignore
        settings.validate_settings()
        return settings
    except ValueError as e:
        raise ValueError(f"Invalid application settings: {e}") from e
