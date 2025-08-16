from beanie import Document
from datetime import datetime
from typing import List, Optional
from pydantic import Field
from bson import ObjectId

class Email(Document):
    from_user: ObjectId = Field(alias="from")
    to_users: List[ObjectId] = Field(alias="to")
    subject: str
    body: str
    threadId: ObjectId
    isRead: bool = False
    isDeleted: bool = False
    sentAt: datetime = Field(default_factory=datetime.now)
    attachments: List[str] = Field(default_factory=list)

    class Settings:
        name = "emails"
        indexes = [
            "from_user",
            "to_users",
            "threadId",
            "sentAt",
            "isRead",
            "isDeleted"
        ]

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "from": "507f1f77bcf86cd799439011",
                "to": ["507f1f77bcf86cd799439012"],
                "subject": "Meeting Tomorrow",
                "body": "Hi, let's meet tomorrow at 2 PM.",
                "threadId": "507f1f77bcf86cd799439013",
                "isRead": False,
                "isDeleted": False,
                "sentAt": "2024-01-01T00:00:00Z",
                "attachments": []
            }
        }
    }
