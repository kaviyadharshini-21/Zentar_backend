from beanie import Document
from datetime import datetime
from pydantic import Field
from bson import ObjectId

class Reminder(Document):
    userId: ObjectId
    emailId: ObjectId
    remindAt: datetime
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "reminders"
        indexes = [
            "userId",
            "emailId",
            "remindAt"
        ]

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "userId": "507f1f77bcf86cd799439011",
                "emailId": "507f1f77bcf86cd799439012",
                "remindAt": "2024-01-02T00:00:00Z",
                "createdAt": "2024-01-01T00:00:00Z"
            }
        }
    }
