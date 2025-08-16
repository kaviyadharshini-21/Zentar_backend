import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "zentar_email")
    
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
    
    # Google Calendar API Configuration
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_CALENDAR_TOKEN_FILE: str = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "token.pickle")
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Default Settings
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "UTC")
    
    # Working Hours (24-hour format)
    DEFAULT_WORKING_HOURS: tuple = (9, 17)  # 9 AM to 5 PM
    
    # Meeting Settings
    DEFAULT_MEETING_DURATION: int = int(os.getenv("DEFAULT_MEETING_DURATION", "60"))  # minutes
    BUFFER_TIME_BETWEEN_MEETINGS: int = int(os.getenv("BUFFER_TIME_BETWEEN_MEETINGS", "15"))  # minutes
    
    # AI Assistant Settings
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.1"))
    MAX_ALTERNATIVES_SUGGESTED: int = int(os.getenv("MAX_ALTERNATIVES_SUGGESTED", "3"))
    ENABLE_CONFLICT_DETECTION: bool = os.getenv("ENABLE_CONFLICT_DETECTION", "True").lower() == "true"
    ENABLE_SMART_SCHEDULING: bool = os.getenv("ENABLE_SMART_SCHEDULING", "True").lower() == "true"
    
    # Notification Settings
    DEFAULT_REMINDER_MINUTES: List[int] = [15, 60]  # 15 minutes and 1 hour before

settings = Settings()
