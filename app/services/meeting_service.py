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
            # Check if credentials file exists
            if not self.credentials_file or not os.path.exists(self.credentials_file):
                print(f"❌ Google Calendar credentials file not found: {self.credentials_file}")
                print("📝 To use Google Calendar, please:")
                print("   1. Go to Google Cloud Console")
                print("   2. Enable Google Calendar API")
                print("   3. Create credentials (OAuth 2.0 Client ID)")
                print("   4. Download credentials.json to your project root")
                print("   5. Set GOOGLE_CALENDAR_CREDENTIALS_FILE in your .env file")
                return False
            
            creds = None
            
            # Load existing token
            if self.token_file and os.path.exists(self.token_file):
                try:
                    with open(self.token_file, 'rb') as token:
                        creds = pickle.load(token)
                except Exception as e:
                    print(f"⚠️ Could not load existing token: {e}")
                    creds = None
            
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
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, SCOPES)
                        creds = flow.run_local_server(port=0)
                        print("✅ New credentials obtained")
                    except Exception as e:
                        print(f"❌ Failed to obtain new credentials: {e}")
                        return False
                
                # Save credentials for next run
                if self.token_file:
                    try:
                        with open(self.token_file, 'wb') as token:
                            pickle.dump(creds, token)
                    except Exception as e:
                        print(f"⚠️ Could not save token: {e}")
            
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
    
    def add_event(self, event: CalendarEvent) -> Optional[str]:
        """Alias for create_event method"""
        return self.create_event(event)
    
    def get_event(self, event_id: str, calendar_id: str = "primary") -> Optional[Dict]:
        """Get a specific event by ID"""
        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Normalize the event data to match the format from get_events
            if event and isinstance(event, dict):
                # Normalize start and end times
                start_data = event.get('start', {})
                end_data = event.get('end', {})
                
                if isinstance(start_data, str):
                    start = start_data
                elif isinstance(start_data, dict):
                    start = start_data.get('dateTime', start_data.get('date'))
                else:
                    start = None
                
                if isinstance(end_data, str):
                    end = end_data
                elif isinstance(end_data, dict):
                    end = end_data.get('dateTime', end_data.get('date'))
                else:
                    end = None
                
                # Normalize attendees
                attendees = []
                raw_attendees = event.get('attendees', [])
                if raw_attendees:
                    for att in raw_attendees:
                        if isinstance(att, str):
                            attendees.append(att)
                        elif isinstance(att, dict) and att.get('email'):
                            attendees.append(att.get('email'))
                
                # Normalize organizer
                organizer = event.get('organizer', {})
                if isinstance(organizer, str):
                    organizer = {'email': organizer}
                elif not isinstance(organizer, dict):
                    organizer = {}
                
                # Return normalized event
                return {
                    'id': event.get('id', ''),
                    'summary': event.get('summary', 'No Title'),
                    'description': event.get('description', ''),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'attendees': attendees,
                    'status': event.get('status', ''),
                    'html_link': event.get('htmlLink', ''),
                    'organizer': organizer,
                    'created': event.get('created', '')
                }
            
            return event
        except HttpError as error:
            print(f"❌ Error getting event: {error}")
            return None
    
    def get_events(self, 
                   start_date: datetime = None, 
                   end_date: datetime = None,
                   calendar_id: str = "primary",
                   max_results: int = 100) -> List[Dict]:
        """Get events from calendar"""
        try:
            if not self.service:
                print("❌ Calendar service not initialized. Please authenticate first.")
                return []
                
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
                # Ensure event is a dictionary and has required fields
                if not isinstance(event, dict):
                    print(f"Warning: Skipping non-dict event in get_events: {type(event)}")
                    continue
                    
                # Normalize start and end times - handle both string and dict formats
                start_data = event.get('start', {})
                end_data = event.get('end', {})
                
                # Handle different start/end formats from Google Calendar API
                if isinstance(start_data, str):
                    start = start_data
                elif isinstance(start_data, dict):
                    start = start_data.get('dateTime', start_data.get('date'))
                else:
                    print(f"Warning: Skipping event with invalid start data format in get_events: {event.get('id', 'unknown')}")
                    continue
                
                if isinstance(end_data, str):
                    end = end_data
                elif isinstance(end_data, dict):
                    end = end_data.get('dateTime', end_data.get('date'))
                else:
                    print(f"Warning: Skipping event with invalid end data format in get_events: {event.get('id', 'unknown')}")
                    continue
                
                # Skip if we couldn't extract valid start/end times
                if not start or not end:
                    print(f"Warning: Skipping event with missing start/end times in get_events: {event.get('id', 'unknown')}")
                    continue
                
                # Normalize attendees - handle both string and dict formats
                attendees = []
                raw_attendees = event.get('attendees', [])
                if raw_attendees:
                    for att in raw_attendees:
                        if isinstance(att, str):
                            attendees.append(att)
                        elif isinstance(att, dict) and att.get('email'):
                            attendees.append(att.get('email'))
                
                # Normalize organizer - handle both string and dict formats
                organizer = event.get('organizer', {})
                if isinstance(organizer, str):
                    organizer = {'email': organizer}
                elif not isinstance(organizer, dict):
                    organizer = {}
                
                parsed_events.append({
                    'id': event.get('id', ''),
                    'summary': event.get('summary', 'No Title'),
                    'description': event.get('description', ''),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'attendees': attendees,
                    'status': event.get('status', ''),
                    'html_link': event.get('htmlLink', ''),
                    'organizer': organizer,
                    'created': event.get('created', '')
                })
            
            return parsed_events
            
        except HttpError as error:
            print(f"❌ Error getting events: {error}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error getting events: {e}")
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
        
                 # Sort events by start time (with safety checks)
        def safe_get_start_time(event):
            # Start is already normalized to string in get_events
            if isinstance(event, dict):
                return event.get('start', '')
            return ''
        
        all_events.sort(key=safe_get_start_time)
        
        free_slots = []
        current_time = start_date
        
        for event in all_events:
            # Ensure event has valid start and end times
            if not isinstance(event, dict):
                print(f"Warning: Skipping non-dict event in find_free_slots: {event}")
                continue
                
            start_time = event.get('start')
            end_time = event.get('end')
            
            if not start_time or not end_time:
                print(f"Warning: Skipping event with missing start/end times in find_free_slots: {event.get('id', 'unknown')}")
                continue
                
            try:
                event_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError as dt_error:
                print(f"Warning: Could not parse datetime for event in find_free_slots: {dt_error}")
                continue
            
                    # Convert to local timezone if needed
        if event_start.tzinfo is None:
            event_start = self.calendar_manager.default_timezone.localize(event_start)
        if event_end.tzinfo is None:
            event_end = self.calendar_manager.default_timezone.localize(event_end)
        
        # Ensure current_time is timezone-aware for comparison
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        
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
            # Ensure event datetimes are timezone-aware
            start_dt = event.start_datetime
            end_dt = event.end_datetime
            
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            
            events = self.calendar_manager.get_events(
                start_dt - timedelta(hours=1),
                end_dt + timedelta(hours=1),
                calendar_id
            )
            
            for existing_event in events:
                # Ensure existing_event is a dictionary and has valid start/end data
                if not isinstance(existing_event, dict):
                    print(f"Warning: Skipping non-dict existing_event in detect_conflicts: {type(existing_event)}")
                    continue
                    
                start_time = existing_event.get('start')
                end_time = existing_event.get('end')
                
                if not start_time or not end_time:
                    print(f"Warning: Skipping existing_event with missing start/end times in detect_conflicts: {existing_event.get('id', 'unknown')}")
                    continue
                
                try:
                    existing_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    existing_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    
                    # Check for overlap
                    if (event.start_datetime < existing_end and event.end_datetime > existing_start):
                        conflicts.append({
                            'calendar_id': calendar_id,
                            'conflicting_event': existing_event,
                            'overlap_start': max(event.start_datetime, existing_start),
                            'overlap_end': min(event.end_datetime, existing_end)
                        })
                except ValueError as dt_error:
                    print(f"Warning: Could not parse datetime for existing_event in detect_conflicts: {dt_error}")
                    continue
        
        return conflicts
    
    def suggest_alternatives(self, event: CalendarEvent, num_suggestions: int = 3) -> List[CalendarEvent]:
        """Suggest alternative times for conflicting events"""
        duration_minutes = int((event.end_datetime - event.start_datetime).total_seconds() / 60)
        
        # Look for alternatives in the next 7 days
        start_dt = event.start_datetime
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
            
        search_start = start_dt.replace(hour=self.working_hours[0], minute=0)
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
    
    @staticmethod
    def _ensure_timezone_aware(dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware, defaulting to UTC if naive"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def __init__(self):
        self.calendar_manager = GoogleCalendarManager()
        self.scheduler = SmartScheduler(self.calendar_manager)
        self.ai_assistant = AICalendarAssistant(self.calendar_manager, self.scheduler)
        
        # Initialize Google Calendar if credentials are available
        if os.path.exists(settings.GOOGLE_CALENDAR_CREDENTIALS_FILE):
            self.calendar_manager.authenticate()
    
    @staticmethod
    async def get_user_meetings(user_id: str, page: int = 1, limit: int = 20) -> MeetingListResponse:
        """Get all meetings for a user from Google Calendar (as organizer or participant)"""
        try:
            # Try to use Google Calendar first
            try:
                # Initialize calendar manager
                calendar_manager = GoogleCalendarManager()
                if calendar_manager.authenticate():
                    # Get user's email from database for calendar lookup
                    user = await User.get(ObjectId(user_id))
                    if not user or not hasattr(user, 'email'):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User email not found"
                        )
                    
                    # Get current time and calculate date range
                    now = datetime.now(timezone.utc)
                    start_date = now - timedelta(days=30)  # Get meetings from last 30 days
                    end_date = now + timedelta(days=365)   # Get meetings up to next year
                    
                    # Ensure start_date and end_date are timezone-aware
                    if start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=timezone.utc)
                    if end_date.tzinfo is None:
                        end_date = end_date.replace(tzinfo=timezone.utc)
                    
                    # Fetch events from Google Calendar
                    events = calendar_manager.get_events(
                        calendar_id='primary',
                        start_date=start_date,
                        end_date=end_date,
                        max_results=limit * 10  # Get more events to allow for pagination
                    )
                    # Filter events where user is organizer or attendee
                    user_meetings = []
                    for event in events:
                        # Ensure event is a dictionary
                        if not isinstance(event, dict):
                            print(f"Warning: Skipping non-dict event: {type(event)}")
                            continue
                            
                        # Check if user is organizer
                        organizer_email = event.get('organizer', {}).get('email') if isinstance(event.get('organizer'), dict) else None
                        if organizer_email == user.email:
                            user_meetings.append(event)
                            continue
                            
                                                 # Check if user is attendee
                        attendees = event.get('attendees', [])
                        if attendees:
                            for attendee in attendees:
                                # Attendees are already normalized to strings in get_events
                                if attendee == user.email:
                                    user_meetings.append(event)
                                    break
                    
                                         # Sort by start time (with safety checks)
                    def safe_get_datetime(event):
                        # Start is already normalized to string in get_events
                        return event.get('start', '')
                    
                    user_meetings.sort(key=safe_get_datetime)
                    
                    # Apply pagination
                    skip = (page - 1) * limit
                    paginated_meetings = user_meetings[skip:skip + limit]
                    total = len(user_meetings)
                                         # Convert to MeetingResponse format
                    meeting_responses = []
                    for event in paginated_meetings:
                        try:
                            # Now start and end are already normalized strings from get_events
                            start_time = event.get('start')
                            end_time = event.get('end')
                            
                            if start_time and end_time:
                                # Safe datetime parsing
                                try:
                                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                                except ValueError as dt_error:
                                    print(f"Warning: Could not parse datetime for event {event.get('id', 'unknown')}: {dt_error}")
                                    continue
                                
                                # Handle attendees - they're already normalized to strings
                                participants = event.get('attendees', [])
                                
                                # Handle organizer - already normalized to dict with email
                                organizer_email = event.get('organizer', {}).get('email', '')
                                
                                meeting_responses.append(MeetingResponse(
                                    id=event.get('id', ''),
                                    organizerId=organizer_email,
                                    participants=participants,  # Already normalized to list of strings
                                    title=event.get('summary', 'No Title'),
                                    description=event.get('description', ''),
                                    startTime=start_dt,
                                    endTime=end_dt,
                                    status='scheduled',
                                    createdAt=datetime.fromisoformat(event.get('created', now.isoformat()).replace('Z', '+00:00'))
                                ))
                        except Exception as event_error:
                            print(f"Warning: Error processing event {event.get('id', 'unknown')}: {event_error}")
                            continue


                    return MeetingListResponse(
                        meetings=meeting_responses,
                        total=total,
                        page=page,
                        limit=limit
                    )
            except Exception as calendar_error:
                print(f"Google Calendar not availabl {calendar_error}")
        
        except Exception as e:
            print(f"Error fetching meetings: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching meetings: {str(e)}"
            )

    @staticmethod
    async def create_meeting(user_id: str, meeting_data: MeetingCreate) -> MeetingResponse:
        """Create a new meeting with fallback to database if Google Calendar is not available"""
        try:
            # Get user's email from database
            user = await User.get(ObjectId(user_id))
            if not user or not hasattr(user, 'email'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User email not found"
                )


            # Verify all participants exist and get their emails
            participant_emails = []
            participant_ids = []

            for participant_input in meeting_data.participants:
                # Check if the input is an email or user ID
                if '@' in participant_input:
                    # It's an email, find the user by email
                    participant = await User.find_one({"email": participant_input})
                    if not participant:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Participant with email {participant_input} not found"
                        )
                    participant_emails.append(participant.email)
                    participant_ids.append(ObjectId(str(participant.id)))
                else:
                    # It's a user ID, validate it's a valid ObjectId
                    try:
                        user_object_id = ObjectId(participant_input)
                        participant = await User.get(user_object_id)
                        if not participant or not hasattr(participant, 'email'):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Participant with ID {participant_input} not found or has no email"
                            )
                        participant_emails.append(participant.email)
                        participant_ids.append(ObjectId(str(participant.id)))
                    except Exception:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Invalid participant ID format: {participant_input}. "
                                "Must be a valid ObjectId or email address."
                            )
                        )

            # Check if meeting time is valid
            if meeting_data.startTime >= meeting_data.endTime:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start time must be before end time"
                )

            # Ensure both datetimes are timezone-aware for comparison
            now_utc = datetime.now(timezone.utc)
            start_time = meeting_data.startTime
            end_time = meeting_data.endTime
            
            # If start_time is timezone-naive, assume it's in UTC
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            
            # If end_time is timezone-naive, assume it's in UTC
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            
            if start_time <= now_utc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start time must be in the future"
                )

            # Try to use Google Calendar first
            try:
                calendar_manager = GoogleCalendarManager()

                if calendar_manager.authenticate():
                    calendar_event = CalendarEvent(
                        summary=meeting_data.title,
                        description=meeting_data.description,
                        start_datetime=meeting_data.startTime,
                        end_datetime=meeting_data.endTime,
                        attendees=participant_emails,
                        timezone=settings.DEFAULT_TIMEZONE
                    )

                    # Conflict detection (if enabled)
                    if getattr(settings, 'ENABLE_CONFLICT_DETECTION', False):
                        service = MeetingService()
                        if service.scheduler:
                            conflicts = service.scheduler.detect_conflicts(calendar_event)
                            if conflicts:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Meeting time conflicts detected: {conflicts}"
                                )

                                        # Add to Google Calend
                    event_id = calendar_manager.add_event(calendar_event)
                    if event_id:
                        created_event = calendar_manager.get_event(event_id, 'primary')
                        if created_event and isinstance(created_event, dict):
                            # Now the event data is already normalized from get_event
                            start_time = created_event.get('start')
                            end_time = created_event.get('end')
                            
                            start_dt = meeting_data.startTime
                            end_dt = meeting_data.endTime
                            
                            if start_time:
                                try:
                                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                except ValueError:
                                    start_dt = meeting_data.startTime
                            
                            if end_time:
                                try:
                                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                                except ValueError:
                                    end_dt = meeting_data.endTime
                            
                            # Attendees are already normalized to strings
                            attendees = created_event.get('attendees', [])
                            
                            # Organizer is already normalized to dict with email
                            organizer_email = created_event.get('organizer', {}).get('email', user.email)
                            
                            return MeetingResponse(
                                id=created_event.get('id', ''),
                                organizerId=organizer_email,
                                participants=attendees,
                                title=created_event.get('summary', meeting_data.title),
                                description=created_event.get('description', meeting_data.description),
                                startTime=start_dt,
                                endTime=end_dt,
                                status='scheduled',
                                createdAt=datetime.fromisoformat(
                                    created_event.get(
                                        'created',
                                        datetime.now(timezone.utc).isoformat()
                                    ).replace('Z', '+00:00')
                                )
                            )
                else:
                    raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Not authenticated to the calender"
                    )
            except Exception as calendar_error:
                print(f"Google Calendar not available, falling back to database: {calendar_error}")

            # Fallback to database if Google Calendar fails
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
                participants=[str(pid) for pid in meeting.participants],
                title=meeting.title,
                description=meeting.description,
                startTime=meeting.startTime,
                endTime=meeting.endTime,
                status=meeting.status,
                createdAt=datetime.now(timezone.utc)
            )

        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating meeting: {str(e)}"
            )

    @staticmethod
    async def get_meeting(meeting_id: str, user_id: str) -> MeetingResponse:
        """Get meeting details with fallback to database if Google Calendar is not available"""
        try:
            # Try to use Google Calendar first
            try:
                # Initialize calendar manager
                calendar_manager = GoogleCalendarManager()
                if calendar_manager.authenticate():
                    # Get user's email from database for calendar lookup
                    user = await User.get(ObjectId(user_id))
                    if not user or not hasattr(user, 'email'):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User email not found"
                        )
                    
                    # Fetch the specific event from Google Calendar
                    event = calendar_manager.get_event(meeting_id, 'primary')
                    if event and isinstance(event, dict):
                        # Verify user has access to this meeting
                        user_has_access = False
                        organizer_data = event.get('organizer', {})
                        if isinstance(organizer_data, dict) and organizer_data.get('email') == user.email:
                            user_has_access = True
                        elif event.get('attendees'):
                            for attendee in event['attendees']:
                                if isinstance(attendee, dict) and attendee.get('email') == user.email:
                                    user_has_access = True
                                    break

                            start_time = event.get('start')
                            end_time = event.get('end')
                            
                            if start_time and end_time:
                                try:
                                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                                    
                                    # Attendees are already normalized to strings
                                    attendees = event.get('attendees', [])
                                    
                                    return MeetingResponse(
                                        id=event.get('id', ''),
                                        organizerId=organizer_data.get('email', '') if isinstance(organizer_data, dict) else '',
                                        participants=attendees,
                                        title=event.get('summary', 'No Title'),
                                        description=event.get('description', ''),
                                        startTime=start_dt,
                                        endTime=end_dt,
                                        status='scheduled',
                                        createdAt=datetime.fromisoformat(event.get('created', datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00'))
                                    )
                                except ValueError as dt_error:
                                    print(f"Warning: Could not parse datetime for event {meeting_id}: {dt_error}")
                                    return None
            except Exception as calendar_error:
                print(f"Google Calendar not available, falling back to database: {calendar_error}")
            
            # Fallback to database if Google Calendar fails
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
                createdAt=meeting.created_at if hasattr(meeting, 'created_at') else datetime.now(timezone.utc)
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
                participant_ids = []
                for participant_input in meeting_data.participants:
                    if '@' in participant_input:
                        # It's an email, find the user by email
                        participant = await User.find_one({"email": participant_input})
                        if not participant:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Participant with email {participant_input} not found"
                            )
                        participant_ids.append(participant.id)
                    else:
                        # It's a user ID, validate it's a valid ObjectId
                        try:
                            user_object_id = ObjectId(participant_input)
                            participant = await User.get(user_object_id)
                            if not participant:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Participant with ID {participant_input} not found"
                                )
                            participant_ids.append(participant.id)
                        except Exception:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Invalid participant ID format: {participant_input}. Must be a valid ObjectId or email address."
                            )
                update_data["participants"] = participant_ids
            
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
                # Ensure both datetimes are timezone-aware for comparison
                start_time = meeting_data.startTime
                end_time = meeting_data.endTime
                
                # If start_time is timezone-naive, assume it's in UTC
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                
                # If end_time is timezone-naive, assume it's in UTC
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
                
                if start_time >= end_time:
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
                createdAt=updated_meeting.created_at if hasattr(updated_meeting, 'created_at') else datetime.now(timezone.utc)
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
            
            # Ensure both datetimes are timezone-aware
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
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
