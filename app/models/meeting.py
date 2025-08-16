from beanie import Document
from datetime import datetime
from typing import List
from pydantic import Field
from bson import ObjectId

class Meeting(Document):
    organizerId: ObjectId
    participants: List[ObjectId]
    title: str
    description: str
    startTime: datetime
    endTime: datetime
    status: str = Field(default="scheduled")  # scheduled, completed, cancelled

    class Settings:
        name = "meetings"
        indexes = [
            "organizerId",
            "participants",
            "startTime",
            "status"
        ]

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "organizerId": "507f1f77bcf86cd799439011",
                "participants": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"],
                "title": "Project Review Meeting",
                "description": "Weekly project review and planning session",
                "startTime": "2024-01-02T14:00:00Z",
                "endTime": "2024-01-02T15:00:00Z",
                "status": "scheduled"
            }
        }
    }
