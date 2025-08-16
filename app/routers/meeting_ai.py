from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.meeting_service import MeetingService
from app.auth.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/meetings/ai", tags=["AI Meeting Management"])

class NaturalLanguageCommand(BaseModel):
    command: str = "Find free time for 1 hour meeting tomorrow"

class MeetingNotes(BaseModel):
    notes: str

class FreeSlotsRequest(BaseModel):
    duration_minutes: int = 60
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@router.post("/command")
async def process_natural_language_command(
    command_data: NaturalLanguageCommand,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Process natural language meeting commands using AI
    
    Examples:
    - "Schedule meeting tomorrow at 2 PM with john@example.com"
    - "Find free time for 1 hour meeting next week"
    - "Create daily standup at 9 AM starting Monday"
    """
    try:
        result = await MeetingService.process_natural_language_command(
            str(current_user.id), 
            command_data.command
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/summarize-notes")
async def summarize_meeting_notes(
    notes_data: MeetingNotes,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Summarize meeting notes and extract action items using AI
    
    This endpoint analyzes meeting notes to provide:
    - Concise summary
    - Key action items with assignees
    - Important decisions made
    - Follow-up items
    """
    try:
        result = await MeetingService.summarize_meeting_notes(notes_data.notes)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/find-free-slots")
async def find_free_slots(
    request: FreeSlotsRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Find available time slots for scheduling meetings
    
    This endpoint uses smart scheduling to find optimal meeting times
    considering working hours, existing meetings, and buffer times.
    """
    try:
        result = await MeetingService.find_free_slots(
            str(current_user.id),
            request.duration_minutes,
            request.start_date,
            request.end_date
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/calendar-status")
async def get_calendar_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the status of Google Calendar integration
    """
    try:
        service = MeetingService()
        calendar_connected = service.calendar_manager.service is not None
        ai_configured = service.ai_assistant.model is not None
        
        return {
            "calendar_connected": calendar_connected,
            "ai_configured": ai_configured,
            "conflict_detection_enabled": service.scheduler is not None,
            "working_hours": service.scheduler.working_hours if service.scheduler else None,
            "buffer_time": service.scheduler.break_duration if service.scheduler else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/suggest-alternatives")
async def suggest_alternative_times(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get alternative meeting times when conflicts are detected
    """
    try:
        # Get the meeting details
        meeting = await MeetingService.get_meeting(meeting_id, str(current_user.id))
        
        # Create calendar event for conflict detection
        from app.services.meeting_service import CalendarEvent
        calendar_event = CalendarEvent(
            summary=meeting.title,
            description=meeting.description,
            start_datetime=meeting.startTime,
            end_datetime=meeting.endTime,
            timezone="UTC"
        )
        
        # Get service instance and suggest alternatives
        service = MeetingService()
        alternatives = service.scheduler.suggest_alternatives(calendar_event)
        
        formatted_alternatives = []
        for alt in alternatives:
            formatted_alternatives.append({
                "start": alt.start_datetime.isoformat(),
                "end": alt.end_datetime.isoformat(),
                "start_formatted": alt.start_datetime.strftime('%A, %B %d at %I:%M %p'),
                "end_formatted": alt.end_datetime.strftime('%I:%M %p'),
                "title": alt.summary,
                "description": alt.description
            })
        
        return {
            "success": True,
            "alternatives": formatted_alternatives,
            "original_meeting": {
                "id": meeting.id,
                "title": meeting.title,
                "start": meeting.startTime.isoformat(),
                "end": meeting.endTime.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/working-hours")
async def get_working_hours(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current working hours configuration
    """
    try:
        service = MeetingService()
        return {
            "working_hours": service.scheduler.working_hours,
            "buffer_time_minutes": service.scheduler.break_duration,
            "timezone": service.calendar_manager.default_timezone.zone
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
