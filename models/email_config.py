# from pydantic import BaseModel
# from fastapi_mail import ConnectionConfig

# class EmailSettings(BaseModel):
#     MAIL_USERNAME: str = "connect@projectdevops.in"
#     MAIL_PASSWORD: str = "kbcfzhilrdtithsr"  # Use the App Password
#     MAIL_FROM: str = "connect@projectdevops.in"
#     MAIL_PORT: int = 587  # TLS (or 465 for SSL)
#     MAIL_SERVER: str = "smtp.gmail.com"
#     MAIL_STARTTLS: bool = True  # Correct field name
#     MAIL_SSL_TLS: bool = False  # Correct field name
#     MAIL_FROM_NAME: str = "Project DevOps"

# settings = EmailSettings()

# conf = ConnectionConfig(
#     MAIL_USERNAME=settings.MAIL_USERNAME,
#     MAIL_PASSWORD=settings.MAIL_PASSWORD,
#     MAIL_FROM=settings.MAIL_FROM,
#     MAIL_PORT=settings.MAIL_PORT,
#     MAIL_SERVER=settings.MAIL_SERVER,
#     MAIL_STARTTLS=settings.MAIL_STARTTLS,  # Corrected field
#     MAIL_SSL_TLS=settings.MAIL_SSL_TLS     # Corrected field
# )

import os
from pydantic import BaseModel
from fastapi_mail import ConnectionConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class EmailSettings(BaseModel):
    MAIL_USERNAME: str = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD: str = os.environ.get("MAIL_PASSWORD")
    MAIL_FROM: str = os.environ.get("MAIL_FROM")
    MAIL_PORT: int = int(os.environ.get("MAIL_PORT", 587))  # Default to 587 if not set
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER")
    MAIL_STARTTLS: bool = os.environ.get("MAIL_STARTTLS", "True").lower() in ("true", "1")
    MAIL_SSL_TLS: bool = os.environ.get("MAIL_SSL_TLS", "False").lower() in ("true", "1")
    MAIL_FROM_NAME: str = os.environ.get("MAIL_FROM_NAME")

settings = EmailSettings()

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS
)
