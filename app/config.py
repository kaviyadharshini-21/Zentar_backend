import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "zentar_email")
    

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    EMAIL_SERVER = os.getenv("EMAIL_SERVER")
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_PORT = os.getenv("EMAIL_PORT")


    # IMAP configuration
    IMAP_USERNAME = os.getenv("IMAP_USERNAME", EMAIL_USERNAME)  # defaults to EMAIL_USERNAME if not set
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", EMAIL_PASSWORD)
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT = os.getenv("IMAP_PORT", 993)

    GOOGLE_CALENDAR_CREDENTIALS_FILE = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials_file.json")
    GOOGLE_CALENDAR_TOKEN_FILE = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "token.pickle")
    SCOPES = [os.getenv("SCOPES")]
    DEFAULT_TIMEZONE = "Asia/Kolkata" 

    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-make-it-long-and-secure")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

settings = Settings()
