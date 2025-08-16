from beanie import Document
from datetime import datetime
from typing import List
from pydantic import Field
from bson import ObjectId

class Thread(Document):
    participants: List[ObjectId]
    emails: List[ObjectId] = Field(default_factory=list)
    lastUpdated: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "threads"
        indexes = [
            "participants",
            "lastUpdated"
        ]

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "participants": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"],
                "emails": ["507f1f77bcf86cd799439013", "507f1f77bcf86cd799439014"],
                "lastUpdated": "2024-01-01T00:00:00Z"
            }
        }
    }
