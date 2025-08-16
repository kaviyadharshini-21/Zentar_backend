from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

class EmailBase(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    attachments: Optional[List[str]] = Field(default_factory=list)

class EmailCreate(EmailBase):
    to_users: List[str] = Field(..., min_items=1)  # List of user IDs as strings

class EmailResponse(EmailBase):
    id: str
    from_user: str
    to_users: List[str]
    threadId: str
    isRead: bool
    isDeleted: bool
    sentAt: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }
    )

class EmailUpdate(BaseModel):
    isRead: Optional[bool] = None
    isDeleted: Optional[bool] = None

class EmailListResponse(BaseModel):
    emails: List[EmailResponse]
    total: int
    page: int
    limit: int
