from beanie import Document
from datetime import datetime
from typing import Dict, Optional
from pydantic import Field

class User(Document):
    name: str
    email: str = Field(unique=True)
    password: str
    avatar: Optional[str] = None
    settings: Dict = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            "email",  # Unique index on email
        ]

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "hashed_password",
                "avatar": "https://example.com/avatar.jpg",
                "settings": {"theme": "dark"},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z"
            }
        }
    }
