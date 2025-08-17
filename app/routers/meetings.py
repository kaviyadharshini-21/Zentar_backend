from fastapi import APIRouter, Depends, Query, status
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse, MeetingListResponse
from app.services.meeting_service import MeetingService
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/meetings", tags=["Meetings"])

@router.get("", response_model=MeetingListResponse)
async def get_meetings(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """Get all meetings for the current user"""
    return await MeetingService.get_user_meetings(str(current_user.id), page, limit)

@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    meeting_data: MeetingCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new meeting"""
    return await MeetingService.create_meeting(str(current_user.id), meeting_data)

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get meeting details"""
    return await MeetingService.get_meeting(meeting_id, str(current_user.id))

@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a meeting"""
    return await MeetingService.update_meeting(meeting_id, str(current_user.id), meeting_data)

@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a meeting"""
    await MeetingService.delete_meeting(meeting_id, str(current_user.id))
    return None
