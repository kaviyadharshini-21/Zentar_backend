from fastapi import APIRouter, Depends, Query, status
from typing import List
from app.models.user import User
from app.schemas.email import EmailCreate, EmailResponse, EmailListResponse
from app.services.email_service import EmailService
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/emails", tags=["Emails"])

@router.get("/inbox", response_model=EmailListResponse)
async def get_inbox(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """Get inbox emails for the current user"""
    return await EmailService.get_inbox_emails(str(current_user.id), page, limit)

@router.get("/thread/{thread_id}", response_model=List[EmailResponse])
async def get_thread_emails(
    thread_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all emails in a thread"""
    return await EmailService.get_thread_emails(thread_id, str(current_user.id))

@router.post("/send", response_model=EmailResponse, status_code=status.HTTP_201_CREATED)
async def send_email(
    email_data: EmailCreate,
    current_user: User = Depends(get_current_user)
):
    """Send a new email"""
    return await EmailService.send_email(str(current_user.id), email_data)

@router.post("/{email_id}/read", response_model=EmailResponse)
async def mark_email_read(
    email_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark an email as read"""
    return await EmailService.mark_email_read(email_id, str(current_user.id))

@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email(
    email_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an email (soft delete)"""
    await EmailService.delete_email(email_id, str(current_user.id))
    return None
