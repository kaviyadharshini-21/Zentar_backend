from datetime import datetime
from typing import List
from fastapi import HTTPException, status
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse, MeetingListResponse
from bson import ObjectId

class MeetingService:
    @staticmethod
    async def get_user_meetings(user_id: str, page: int = 1, limit: int = 20) -> MeetingListResponse:
        """Get all meetings for a user (as organizer or participant)"""
        try:
            skip = (page - 1) * limit
            
            # Find meetings where user is organizer or participant
            meetings = await Meeting.find({
                "$or": [
                    {"organizerId": ObjectId(user_id)},
                    {"participants": ObjectId(user_id)}
                ]
            }).sort([("startTime", 1)]).skip(skip).limit(limit).to_list()
            
            # Get total count
            total = await Meeting.count_documents({
                "$or": [
                    {"organizerId": ObjectId(user_id)},
                    {"participants": ObjectId(user_id)}
                ]
            })
            
            meeting_responses = []
            for meeting in meetings:
                meeting_responses.append(MeetingResponse(
                    id=str(meeting.id),
                    organizerId=str(meeting.organizerId),
                    participants=[str(participant_id) for participant_id in meeting.participants],
                    title=meeting.title,
                    description=meeting.description,
                    startTime=meeting.startTime,
                    endTime=meeting.endTime,
                    status=meeting.status
                ))
            
            return MeetingListResponse(
                meetings=meeting_responses,
                total=total,
                page=page,
                limit=limit
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching meetings: {str(e)}"
            )

    @staticmethod
    async def create_meeting(user_id: str, meeting_data: MeetingCreate) -> MeetingResponse:
        """Create a new meeting"""
        try:
            # Convert string IDs to ObjectIds
            participant_ids = [ObjectId(user_id_str) for user_id_str in meeting_data.participants]
            
            # Verify all participants exist
            for user_id_str in meeting_data.participants:
                participant = await User.get(ObjectId(user_id_str))
                if not participant:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Participant with ID {user_id_str} not found"
                    )
            
            # Check if meeting time is valid
            if meeting_data.startTime >= meeting_data.endTime:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start time must be before end time"
                )
            
            if meeting_data.startTime <= datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start time must be in the future"
                )
            
            # Create meeting
            meeting = Meeting(
                organizerId=ObjectId(user_id),
                participants=participant_ids,
                title=meeting_data.title,
                description=meeting_data.description,
                startTime=meeting_data.startTime,
                endTime=meeting_data.endTime,
                status="scheduled"
            )
            
            await meeting.insert()
            
            return MeetingResponse(
                id=str(meeting.id),
                organizerId=str(meeting.organizerId),
                participants=[str(participant_id) for participant_id in meeting.participants],
                title=meeting.title,
                description=meeting.description,
                startTime=meeting.startTime,
                endTime=meeting.endTime,
                status=meeting.status
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating meeting: {str(e)}"
            )

    @staticmethod
    async def get_meeting(meeting_id: str, user_id: str) -> MeetingResponse:
        """Get meeting details"""
        try:
            meeting = await Meeting.get(ObjectId(meeting_id))
            if not meeting:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Meeting not found"
                )
            
            # Verify user has access to this meeting
            if ObjectId(user_id) != meeting.organizerId and ObjectId(user_id) not in meeting.participants:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this meeting"
                )
            
            return MeetingResponse(
                id=str(meeting.id),
                organizerId=str(meeting.organizerId),
                participants=[str(participant_id) for participant_id in meeting.participants],
                title=meeting.title,
                description=meeting.description,
                startTime=meeting.startTime,
                endTime=meeting.endTime,
                status=meeting.status
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching meeting: {str(e)}"
            )

    @staticmethod
    async def update_meeting(meeting_id: str, user_id: str, meeting_data: MeetingUpdate) -> MeetingResponse:
        """Update a meeting"""
        try:
            meeting = await Meeting.get(ObjectId(meeting_id))
            if not meeting:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Meeting not found"
                )
            
            # Verify user is the organizer
            if ObjectId(user_id) != meeting.organizerId:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the organizer can update this meeting"
                )
            
            # Build update data
            update_data = {}
            if meeting_data.participants is not None:
                # Verify all participants exist
                for user_id_str in meeting_data.participants:
                    participant = await User.get(ObjectId(user_id_str))
                    if not participant:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Participant with ID {user_id_str} not found"
                        )
                update_data["participants"] = [ObjectId(user_id_str) for user_id_str in meeting_data.participants]
            
            if meeting_data.title is not None:
                update_data["title"] = meeting_data.title
            if meeting_data.description is not None:
                update_data["description"] = meeting_data.description
            if meeting_data.startTime is not None:
                update_data["startTime"] = meeting_data.startTime
            if meeting_data.endTime is not None:
                update_data["endTime"] = meeting_data.endTime
            if meeting_data.status is not None:
                update_data["status"] = meeting_data.status
            
            # Validate time if both start and end times are provided
            if meeting_data.startTime is not None and meeting_data.endTime is not None:
                if meeting_data.startTime >= meeting_data.endTime:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Start time must be before end time"
                    )
            
            await meeting.update({"$set": update_data})
            
            # Get updated meeting
            updated_meeting = await Meeting.get(ObjectId(meeting_id))
            return MeetingResponse(
                id=str(updated_meeting.id),
                organizerId=str(updated_meeting.organizerId),
                participants=[str(participant_id) for participant_id in updated_meeting.participants],
                title=updated_meeting.title,
                description=updated_meeting.description,
                startTime=updated_meeting.startTime,
                endTime=updated_meeting.endTime,
                status=updated_meeting.status
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating meeting: {str(e)}"
            )

    @staticmethod
    async def delete_meeting(meeting_id: str, user_id: str) -> bool:
        """Cancel/delete a meeting"""
        try:
            meeting = await Meeting.get(ObjectId(meeting_id))
            if not meeting:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Meeting not found"
                )
            
            # Verify user is the organizer
            if ObjectId(user_id) != meeting.organizerId:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the organizer can cancel this meeting"
                )
            
            # Soft delete by marking as cancelled
            await meeting.update({"$set": {"status": "cancelled"}})
            
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error cancelling meeting: {str(e)}"
            )
