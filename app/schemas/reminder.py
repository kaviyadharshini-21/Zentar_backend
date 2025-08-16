from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from bson import ObjectId
from typing import List

class ReminderBase(BaseModel):
    emailId: str
    remindAt: datetime

class ReminderCreate(ReminderBase):
    pass

class ReminderResponse(ReminderBase):
    id: str
    userId: str
    createdAt: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }
    )

class ReminderListResponse(BaseModel):
    reminders: List[ReminderResponse]
    total: int
