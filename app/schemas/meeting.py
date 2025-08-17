from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

class MeetingBase(BaseModel):
    participants: List[str] = Field(..., min_items=1, description="List of participant user IDs or email addresses")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    startTime: datetime
    endTime: datetime

class MeetingCreate(MeetingBase):
    pass

class MeetingUpdate(BaseModel):
    participants: Optional[List[str]] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(scheduled|completed|cancelled)$")

class MeetingResponse(MeetingBase):
    id: str
    organizerId: str
    status: str
    createdAt: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }
    )

class MeetingListResponse(BaseModel):
    meetings: List[MeetingResponse]
    total: int
    page: int
    limit: int
