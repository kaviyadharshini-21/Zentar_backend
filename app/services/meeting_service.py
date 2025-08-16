import os
import pickle
import json
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
import pytz
from dataclasses import dataclass, asdict
from pathlib import Path

# Google Calendar API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# AI Integration
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# FastAPI and Database
from fastapi import HTTPException, status
from bson import ObjectId
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse, MeetingListResponse
from app.config import settings

# Google Calendar API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

@dataclass
class CalendarEvent:
    """Data class for calendar events"""
    id: Optional[str] = None
    summary: str = ""
    description: str = ""
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: str = ""
    attendees: List[str] = None
    recurrence: List[str] = None
    reminders: List[Dict] = None
    calendar_id: str = "primary"
    timezone: str = settings.DEFAULT_TIMEZONE
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []
        if self.reminders is None:
            self.reminders = []

class GoogleCalendarManager:
    """Main Google Calendar management class"""
    
    def __init__(self, credentials_file: str = None, token_file: str = None):
        self.credentials_file = credentials_file or settings.GOOGLE_CALENDAR_CREDENTIALS_FILE
        self.token_file = token_file or settings.GOOGLE_CALENDAR_TOKEN_FILE
        self.service = None
        self.credentials = None
        self.default_timezone = pytz.timezone(settings.DEFAULT_TIMEZONE)
        
    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API"""
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        print("🔄 Refreshed existing credentials")
                    except Exception as e:
                        print(f"❌ Failed to refresh credentials: {e}")
                        creds = None
                
                if not creds:
                    if not os.path.exists(self.credentials_file):
                        print(f"❌ Credentials file not found: {self.credentials_file}")
                        print("📝 Please download credentials.json from Google Cloud Console")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("✅ New credentials obtained")
                
                # Save credentials for next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.credentials = creds
            self.service = build('calendar', 'v3', credentials=creds)
            print("✅ Google Calendar API authenticated successfully")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def create_event(self, event: CalendarEvent) -> Optional[str]:
        """Create a new calendar event"""
        try:
            # Prepare event data
            event_body = {
                'summary': event.summary,
                'description': event.description,
                'location': event.location,
                'start': {
                    'dateTime': event.start_datetime.isoformat(),
                    'timeZone': event.timezone,
                },
                'end': {
                    'dateTime': event.end_datetime.isoformat(),
                    'timeZone': event.timezone,
                },
            }
            
            # Add attendees
            if event.attendees:
                event_body['attendees'] = [{'email': email} for email in event.attendees]
            
            # Add recurrence
            if event.recurrence:
                event_body['recurrence'] = event.recurrence
            
            # Add reminders
            if event.reminders:
                event_body['reminders'] = {
                    'useDefault': False,
                    'overrides': event.reminders
                }
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=event.calendar_id, 
                body=event_body
            ).execute()
            
            print(f"✅ Event created: {created_event['id']}")
            return created_event['id']
            
        except HttpError as error:
            print(f"❌ Error creating event: {error}")
            return None
    
    def get_events(self, 
                   start_date: datetime = None, 
                   end_date: datetime = None,
                   calendar_id: str = "primary",
                   max_results: int = 100) -> List[Dict]:
        """Get events from calendar"""
        try:
            if not start_date:
                start_date = datetime.now(self.default_timezone)
            if not end_date:
                end_date = start_date + timedelta(days=30)
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_date.isoformat(),
                timeMax=end_date.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            parsed_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                parsed_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No Title'),
                    'description': event.get('description', ''),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'attendees': [att.get('email') for att in event.get('attendees', [])],
                    'status': event.get('status', ''),
                    'html_link': event.get('htmlLink', '')
                })
            
            return parsed_events
            
        except HttpError as error:
            print(f"❌ Error getting events: {error}")
            return []

class SmartScheduler:
    """Intelligent scheduling with conflict resolution"""
    
    def __init__(self, calendar_manager: GoogleCalendarManager):
        self.calendar_manager = calendar_manager
        self.working_hours = settings.DEFAULT_WORKING_HOURS
        self.break_duration = settings.BUFFER_TIME_BETWEEN_MEETINGS
        
    def find_free_slots(self, 
                       start_date: datetime,
                       end_date: datetime,
                       duration_minutes: int,
                       calendars: List[str] = None) -> List[Tuple[datetime, datetime]]:
        """Find available time slots across multiple calendars"""
        
        if not calendars:
            calendars = ["primary"]
        
        # Get all events from specified calendars
        all_events = []
        for calendar_id in calendars:
            events = self.calendar_manager.get_events(start_date, end_date, calendar_id)
            all_events.extend(events)
        
        # Sort events by start time
        all_events.sort(key=lambda x: x['start'])
        
        free_slots = []
        current_time = start_date
        
        for event in all_events:
            event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
            
            # Convert to local timezone if needed
            if event_start.tzinfo is None:
                event_start = self.calendar_manager.default_timezone.localize(event_start)
            if event_end.tzinfo is None:
                event_end = self.calendar_manager.default_timezone.localize(event_end)
            
            # Check if there's a free slot before this event
            if current_time < event_start:
                slot_duration = (event_start - current_time).total_seconds() / 60
                if slot_duration >= duration_minutes + self.break_duration:
                    # Check if within working hours
                    if self._is_working_hours(current_time, duration_minutes):
                        slot_end = current_time + timedelta(minutes=duration_minutes)
                        free_slots.append((current_time, slot_end))
            
            current_time = max(current_time, event_end + timedelta(minutes=self.break_duration))
        
        # Check for slots after the last event
        if current_time < end_date:
            slot_duration = (end_date - current_time).total_seconds() / 60
            if slot_duration >= duration_minutes and self._is_working_hours(current_time, duration_minutes):
                slot_end = current_time + timedelta(minutes=duration_minutes)
                free_slots.append((current_time, slot_end))
        
        return free_slots[:10]  # Return top 10 slots
    
    def _is_working_hours(self, start_time: datetime, duration_minutes: int) -> bool:
        """Check if time slot is within working hours"""
        start_hour = start_time.hour
        end_time = start_time + timedelta(minutes=duration_minutes)
        end_hour = end_time.hour
        
        return (start_hour >= self.working_hours[0] and 
                end_hour <= self.working_hours[1] and
                start_time.weekday() < 5)  # Monday-Friday
    
    def detect_conflicts(self, event: CalendarEvent, calendars: List[str] = None) -> List[Dict]:
        """Detect scheduling conflicts"""
        if not calendars:
            calendars = ["primary"]
        
        conflicts = []
        
        # Check each calendar for conflicts
        for calendar_id in calendars:
            events = self.calendar_manager.get_events(
                event.start_datetime - timedelta(hours=1),
                event.end_datetime + timedelta(hours=1),
                calendar_id
            )
            
            for existing_event in events:
                existing_start = datetime.fromisoformat(existing_event['start'].replace('Z', '+00:00'))
                existing_end = datetime.fromisoformat(existing_event['end'].replace('Z', '+00:00'))
                
                # Check for overlap
                if (event.start_datetime < existing_end and event.end_datetime > existing_start):
                    conflicts.append({
                        'calendar_id': calendar_id,
                        'conflicting_event': existing_event,
                        'overlap_start': max(event.start_datetime, existing_start),
                        'overlap_end': min(event.end_datetime, existing_end)
                    })
        
        return conflicts
    
    def suggest_alternatives(self, event: CalendarEvent, num_suggestions: int = 3) -> List[CalendarEvent]:
        """Suggest alternative times for conflicting events"""
        duration_minutes = int((event.end_datetime - event.start_datetime).total_seconds() / 60)
        
        # Look for alternatives in the next 7 days
        search_start = event.start_datetime.replace(hour=self.working_hours[0], minute=0)
        search_end = search_start + timedelta(days=7)
        
        free_slots = self.find_free_slots(search_start, search_end, duration_minutes)
        
        alternatives = []
        for i, (start, end) in enumerate(free_slots[:num_suggestions]):
            alt_event = CalendarEvent(
                summary=event.summary,
                description=event.description,
                start_datetime=start,
                end_datetime=end,
                location=event.location,
                attendees=event.attendees.copy(),
                calendar_id=event.calendar_id,
                timezone=event.timezone
            )
            alternatives.append(alt_event)
        
        return alternatives

class AICalendarAssistant:
    """AI-powered calendar assistant using Gemini 2.0"""
    
    def __init__(self, calendar_manager: GoogleCalendarManager, scheduler: SmartScheduler):
        self.calendar_manager = calendar_manager
        self.scheduler = scheduler
        
        # Initialize Gemini if API key is provided
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Safety settings
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        else:
            self.model = None
    
    def parse_natural_language_command(self, command: str) -> Dict[str, Any]:
        """Parse natural language commands using Gemini"""
        
        if not self.model:
            return {}
        
        prompt = f"""
        Parse the following calendar command and extract structured information:
        Command: "{command}"
        
        Extract the following information in JSON format:
        {{
            "action": "create|update|delete|find|list",
            "title": "event title",
            "description": "event description", 
            "date": "YYYY-MM-DD",
            "start_time": "HH:MM",
            "end_time": "HH:MM",
            "duration_minutes": number,
            "location": "location if mentioned",
            "attendees": ["email1", "email2"],
            "recurrence": "daily|weekly|monthly|yearly|none",
            "reminders": [minutes_before],
            "timezone": "timezone if mentioned"
        }}
        
        Today's date is: {datetime.now().strftime('%Y-%m-%d')}
        Current time is: {datetime.now().strftime('%H:%M')}
        
        Examples:
        - "Schedule meeting tomorrow at 2 PM with john@example.com" 
        - "Create daily standup at 9 AM starting Monday"
        - "Find free time for 1 hour meeting next week"
        - "Delete the meeting with client on Friday"
        
        Return only valid JSON without any markdown formatting.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.AI_TEMPERATURE,
                    top_p=0.1,
                    top_k=16,
                    max_output_tokens=1024,
                )
            )
            
            # Clean the response and parse JSON
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            parsed_command = json.loads(response_text)
            return parsed_command
            
        except Exception as e:
            print(f"❌ Error parsing command: {e}")
            return {}
    
    def summarize_meeting_notes(self, meeting_notes: str) -> Dict[str, Any]:
        """Summarize meeting notes and extract action items using Gemini"""
        
        if not self.model:
            return {"success": False, "message": "Gemini AI not configured"}
        
        prompt = f"""
        Analyze the following meeting notes and provide:
        1. A concise summary
        2. Key action items with assignees (if mentioned)
        3. Important decisions made
        4. Follow-up items
        
        Meeting Notes:
        {meeting_notes}
        
        Provide the response in JSON format:
        {{
            "summary": "Brief meeting summary",
            "action_items": [
                {{
                    "task": "Description of task",
                    "assignee": "Person assigned (if mentioned)",
                    "due_date": "Due date if mentioned",
                    "priority": "high|medium|low"
                }}
            ],
            "key_decisions": ["Decision 1", "Decision 2"],
            "follow_ups": ["Follow-up item 1", "Follow-up item 2"],
            "next_meeting": "Date/time if mentioned"
        }}
        
        Return only valid JSON without markdown formatting.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            # Clean and parse response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            summary_data = json.loads(response_text)
            return {
                "success": True,
                "summary_data": summary_data
            }
            
        except Exception as e:
            print(f"❌ Error summarizing notes: {e}")
            return {"success": False, "message": f"Failed to summarize: {e}"}

class MeetingService:
    """Enhanced meeting service with AI-powered calendar management"""
    
    def __init__(self):
        self.calendar_manager = GoogleCalendarManager()
        self.scheduler = SmartScheduler(self.calendar_manager)
        self.ai_assistant = AICalendarAssistant(self.calendar_manager, self.scheduler)
        
        # Initialize Google Calendar if credentials are available
        if os.path.exists(settings.GOOGLE_CALENDAR_CREDENTIALS_FILE):
            self.calendar_manager.authenticate()
    
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
                    status=meeting.status,
                    createdAt=meeting.created_at if hasattr(meeting, 'created_at') else datetime.utcnow()
                ))
            
            return MeetingListResponse(
                meetings=meeting_responses,
                total=total,
                page=page,
                limit=limit
            )
        except Exception as e:
            print(e )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching meetings: {str(e)}"
            )

    @staticmethod
    async def create_meeting(user_id: str, meeting_data: MeetingCreate) -> MeetingResponse:
        """Create a new meeting with smart scheduling and conflict detection"""
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
            
            # If Google Calendar is available, sync the meeting
            service = MeetingService()
            if service.calendar_manager.service:
                try:
                    # Get participant emails
                    participant_emails = []
                    for participant_id in participant_ids:
                        participant = await User.get(participant_id)
                        if participant and hasattr(participant, 'email'):
                            participant_emails.append(participant.email)
                    
                    # Create calendar event
                    calendar_event = CalendarEvent(
                        summary=meeting_data.title,
                        description=meeting_data.description,
                        start_datetime=meeting_data.startTime,
                        end_datetime=meeting_data.endTime,
                        attendees=participant_emails,
                        timezone=settings.DEFAULT_TIMEZONE
                    )
                    
                    # Check for conflicts if enabled
                    if settings.ENABLE_CONFLICT_DETECTION:
                        conflicts = service.scheduler.detect_conflicts(calendar_event)
                        if conflicts:
                            # Return conflict information
                            return MeetingResponse(
                                id=str(meeting.id),
                                organizerId=str(meeting.organizerId),
                                participants=[str(participant_id) for participant_id in meeting.participants],
                                title=meeting.title,
                                description=meeting.description,
                                startTime=meeting.startTime,
                                endTime=meeting.endTime,
                                status="conflict_detected",
                                createdAt=datetime.utcnow(),
                                conflicts=conflicts
                            )
                    
                    # Create calendar event
                    service.calendar_manager.create_event(calendar_event)
                    
                except Exception as e:
                    print(f"Warning: Failed to sync with Google Calendar: {e}")
            
            return MeetingResponse(
                id=str(meeting.id),
                organizerId=str(meeting.organizerId),
                participants=[str(participant_id) for participant_id in meeting.participants],
                title=meeting.title,
                description=meeting.description,
                startTime=meeting.startTime,
                endTime=meeting.endTime,
                status=meeting.status,
                createdAt=datetime.utcnow()
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
                status=meeting.status,
                createdAt=meeting.created_at if hasattr(meeting, 'created_at') else datetime.utcnow()
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
                status=updated_meeting.status,
                createdAt=updated_meeting.created_at if hasattr(updated_meeting, 'created_at') else datetime.utcnow()
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

    @staticmethod
    async def find_free_slots(user_id: str, duration_minutes: int = 60, 
                            start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Find free time slots for a user"""
        try:
            service = MeetingService()
            
            if not start_date:
                start_date = datetime.now(pytz.timezone(settings.DEFAULT_TIMEZONE))
            if not end_date:
                end_date = start_date + timedelta(days=7)
            
            free_slots = service.scheduler.find_free_slots(start_date, end_date, duration_minutes)
            
            formatted_slots = []
            for start, end in free_slots:
                formatted_slots.append({
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "start_formatted": start.strftime('%A, %B %d at %I:%M %p'),
                    "end_formatted": end.strftime('%I:%M %p'),
                    "duration_minutes": duration_minutes
                })
            
            return {
                "success": True,
                "free_slots": formatted_slots,
                "duration_requested": duration_minutes,
                "search_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error finding free slots: {str(e)}"
            )

    @staticmethod
    async def process_natural_language_command(user_id: str, command: str) -> Dict[str, Any]:
        """Process natural language meeting commands"""
        try:
            service = MeetingService()
            
            if not service.ai_assistant.model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="AI assistant not configured. Please set GEMINI_API_KEY."
                )
            
            # Parse the command
            parsed = service.ai_assistant.parse_natural_language_command(command)
            
            if not parsed:
                return {"success": False, "message": "Could not understand the command"}
            
            action = parsed.get('action', '').lower()
            
            if action == 'create':
                # Create meeting from natural language
                # This would need to be implemented based on your specific requirements
                return {"success": False, "message": "Natural language meeting creation not yet implemented"}
            elif action == 'find':
                # Find free time
                duration = parsed.get('duration_minutes', 60)
                return await MeetingService.find_free_slots(user_id, duration)
            else:
                return {"success": False, "message": f"Unknown action: {action}"}
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing command: {str(e)}"
            )

    @staticmethod
    async def summarize_meeting_notes(notes: str) -> Dict[str, Any]:
        """Summarize meeting notes using AI"""
        try:
            service = MeetingService()
            
            if not service.ai_assistant.model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="AI assistant not configured. Please set GEMINI_API_KEY."
                )
            
            result = service.ai_assistant.summarize_meeting_notes(notes)
            return result
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error summarizing notes: {str(e)}"
            )
