from datetime import datetime
from typing import List
from fastapi import HTTPException, status
from app.models.reminder import Reminder
from app.models.email import Email
from app.schemas.reminder import ReminderCreate, ReminderResponse, ReminderListResponse
from bson import ObjectId

class ReminderService:
    @staticmethod
    async def get_user_reminders(user_id: str) -> ReminderListResponse:
        """Get all reminders for a user"""
        try:
            reminders = await Reminder.find({"userId": ObjectId(user_id)}).sort([("remindAt", 1)]).to_list()
            
            reminder_responses = []
            for reminder in reminders:
                reminder_responses.append(ReminderResponse(
                    id=str(reminder.id),
                    userId=str(reminder.userId),
                    emailId=str(reminder.emailId),
                    remindAt=reminder.remindAt,
                    createdAt=reminder.createdAt
                ))
            
            return ReminderListResponse(
                reminders=reminder_responses,
                total=len(reminder_responses)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching reminders: {str(e)}"
            )

    @staticmethod
    async def create_reminder(user_id: str, reminder_data: ReminderCreate) -> ReminderResponse:
        """Create a new reminder"""
        try:
            # Verify the email exists and user has access to it
            email = await Email.get(ObjectId(reminder_data.emailId))
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email not found"
                )
            
            # Check if user has access to this email
            if ObjectId(user_id) not in email.to_users and ObjectId(user_id) != email.from_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this email"
                )
            
            # Check if reminder time is in the future
            if reminder_data.remindAt <= datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reminder time must be in the future"
                )
            
            # Create reminder
            reminder = Reminder(
                userId=ObjectId(user_id),
                emailId=ObjectId(reminder_data.emailId),
                remindAt=reminder_data.remindAt
            )
            
            await reminder.insert()
            
            return ReminderResponse(
                id=str(reminder.id),
                userId=str(reminder.userId),
                emailId=str(reminder.emailId),
                remindAt=reminder.remindAt,
                createdAt=reminder.createdAt
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating reminder: {str(e)}"
            )

    @staticmethod
    async def delete_reminder(reminder_id: str, user_id: str) -> bool:
        """Delete a reminder"""
        try:
            reminder = await Reminder.get(ObjectId(reminder_id))
            if not reminder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reminder not found"
                )
            
            # Verify user owns this reminder
            if reminder.userId != ObjectId(user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this reminder"
                )
            
            await reminder.delete()
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting reminder: {str(e)}"
            )

    @staticmethod
    async def get_due_reminders() -> List[ReminderResponse]:
        """Get all reminders that are due (for background job)"""
        try:
            now = datetime.utcnow()
            due_reminders = await Reminder.find({"remindAt": {"$lte": now}}).to_list()
            
            reminder_responses = []
            for reminder in due_reminders:
                reminder_responses.append(ReminderResponse(
                    id=str(reminder.id),
                    userId=str(reminder.userId),
                    emailId=str(reminder.emailId),
                    remindAt=reminder.remindAt,
                    createdAt=reminder.createdAt
                ))
            
            return reminder_responses
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching due reminders: {str(e)}"
            )
