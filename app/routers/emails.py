from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Optional, Dict, Any
from app.services.email_service import EmailService
from app.auth.jwt import get_current_user
from app.models.user import User
from app.schemas.email import EmailCreate, EmailResponse, EmailListResponse

router = APIRouter(prefix="/emails", tags=["emails"])

@router.post("/compose", response_model=Dict[str, Any])
async def compose_email(
    context: str = Body(..., description="The context/purpose of the email"),
    tone: str = Body("professional", description="Email tone (professional, friendly, formal, casual, persuasive)"),
    length: str = Body("medium", description="Email length (short, medium, long)"),
    recipient_type: str = Body("colleague", description="Type of recipient (colleague, client, manager, friend)"),
    subject_line: Optional[str] = Body(None, description="Optional custom subject line"),
    current_user: User = Depends(get_current_user)
):
    """Compose an email using AI based on user parameters"""
    try:
        email_service = EmailService()
        result = await email_service.compose_email(
            context=context,
            tone=tone,
            length=length,
            recipient_type=recipient_type,
            subject_line=subject_line
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error composing email: {str(e)}"
        )

@router.post("/compose-template", response_model=Dict[str, Any])
async def compose_email_with_template(
    template_type: str = Body(..., description="Type of template (meeting_request, follow_up, thank_you)"),
    context: Dict[str, Any] = Body(..., description="Context data for the template"),
    current_user: User = Depends(get_current_user)
):
    """Compose an email using predefined templates"""
    try:
        email_service = EmailService()
        result = await email_service.compose_email_with_template(
            template_type=template_type,
            context=context
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error composing template email: {str(e)}"
        )

@router.get("/templates", response_model=Dict[str, Any])
async def get_available_templates(current_user: User = Depends(get_current_user)):
    """Get available email templates and their parameters"""
    templates = {
        "meeting_request": {
            "description": "Request a meeting with someone",
            "required_context": ["recipient_name", "purpose", "proposed_time", "duration", "location"],
            "example": {
                "recipient_name": "John Doe",
                "purpose": "Project review discussion",
                "proposed_time": "Tomorrow at 2 PM",
                "duration": "1 hour",
                "location": "Conference Room A"
            }
        },
        "follow_up": {
            "description": "Follow up on previous communication",
            "required_context": ["recipient_name", "previous_interaction", "purpose", "next_steps", "timeline"],
            "example": {
                "recipient_name": "Jane Smith",
                "previous_interaction": "Our meeting last week",
                "purpose": "Check on action items",
                "next_steps": "Schedule follow-up meeting",
                "timeline": "This week"
            }
        },
        "thank_you": {
            "description": "Express gratitude for help or support",
            "required_context": ["recipient_name", "reason", "specific_action", "future_collaboration"],
            "example": {
                "recipient_name": "Mike Johnson",
                "reason": "Help with project",
                "specific_action": "Technical guidance and support",
                "future_collaboration": "Looking forward to working together again"
            }
        }
    }
    
    return {
        "success": True,
        "templates": templates,
        "available_tones": ["professional", "friendly", "formal", "casual", "persuasive"],
        "available_lengths": ["short", "medium", "long"],
        "available_recipient_types": ["colleague", "client", "manager", "friend"]
    }

@router.get("/inbox", response_model=EmailListResponse)
async def get_inbox(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """Get inbox emails for the current user"""
    return await EmailService.get_inbox_emails(str(current_user.id), page, limit)

@router.get("/fetch", response_model=EmailListResponse)
async def fetch_emails(
    count: int = Query(20, ge=1, le=100, description="Number of emails to fetch"),
    enable_ai: bool = Query(False, description="Enable AI processing"),
    current_user: User = Depends(get_current_user)
):
    """Fetch emails with optional AI processing"""
    return await EmailService.get_inbox_emails(str(current_user.id), 1, count)

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
