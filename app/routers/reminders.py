from fastapi import APIRouter, Depends, status
from app.models.user import User
from app.schemas.reminder import ReminderCreate, ReminderResponse, ReminderListResponse
from app.services.reminder_service import ReminderService
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/reminders", tags=["Reminders"])

@router.get("/", response_model=ReminderListResponse)
async def get_reminders(current_user: User = Depends(get_current_user)):
    """Get all reminders for the current user"""
    return await ReminderService.get_user_reminders(str(current_user.id))

@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    reminder_data: ReminderCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new reminder"""
    return await ReminderService.create_reminder(str(current_user.id), reminder_data)

@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a reminder"""
    await ReminderService.delete_reminder(reminder_id, str(current_user.id))
    return None
