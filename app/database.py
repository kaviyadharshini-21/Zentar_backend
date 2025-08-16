from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
from app.models.user import User
from app.models.email import Email
from app.models.thread import Thread
from app.models.reminder import Reminder
from app.models.meeting import Meeting

async def init_db():
    """Initialize database connection and Beanie models"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    
    # Initialize Beanie with the document models
    await init_beanie(
        database=client[settings.DATABASE_NAME],
        document_models=[
            User,
            Email,
            Thread,
            Reminder,
            Meeting
        ]
    )

async def close_db():
    """Close database connection"""
    # Motor client will be closed automatically when the app shuts down
    pass
