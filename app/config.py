from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Standard sync database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


class Settings(BaseSettings):
    # Zoho Mail IMAP Configuration (existente)
    ZOHO_EMAIL: str
    ZOHO_PASSWORD: str
    ZOHO_IMAP_SERVER: str
    ZOHO_IMAP_PORT: int
    ZOHO_FOLDER: str

    # Zoho Mail SMTP Configuration (nuevo)
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USE_TLS: bool = True
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    NOTIFICATION_EMAIL: str
    ALERT_EMAIL: str

    # API Configuration
    API_HOST: str
    API_PORT: int

    # Storage Configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    XML_STORAGE_PATH: Path = BASE_DIR / "data" / "xml_files"
    PROCESSED_DATA_PATH: Path = BASE_DIR / "data" / "processed"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    # return Settings()
    pass


# Crear directorios necesarios si no existen
def create_required_directories():
    settings = get_settings()
    # os.makedirs(settings.XML_STORAGE_PATH, exist_ok=True)
    # os.makedirs(settings.PROCESSED_DATA_PATH, exist_ok=True)


# Llamar a la función cuando se importa el módulo
create_required_directories()
