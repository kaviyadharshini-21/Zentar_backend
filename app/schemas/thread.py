from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List
from bson import ObjectId

class ThreadBase(BaseModel):
    participants: List[str] = Field(..., min_items=2)  # List of user IDs as strings

class ThreadCreate(ThreadBase):
    pass

class ThreadResponse(ThreadBase):
    id: str
    emails: List[str]  # List of email IDs as strings
    lastUpdated: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }
    )

class ThreadListResponse(BaseModel):
    threads: List[ThreadResponse]
    total: int
    page: int
    limit: int
