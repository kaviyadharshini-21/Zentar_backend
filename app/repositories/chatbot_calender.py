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
from app.config import settings

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
    
    def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """Update an existing event"""
        try:
            # Get existing event
            existing_event = self.service.events().get(
                calendarId=event.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            existing_event.update({
                'summary': event.summary or existing_event.get('summary'),
                'description': event.description or existing_event.get('description'),
                'location': event.location or existing_event.get('location'),
            })
            
            if event.start_datetime:
                existing_event['start'] = {
                    'dateTime': event.start_datetime.isoformat(),
                    'timeZone': event.timezone,
                }
            
            if event.end_datetime:
                existing_event['end'] = {
                    'dateTime': event.end_datetime.isoformat(),
                    'timeZone': event.timezone,
                }
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=event.calendar_id,
                eventId=event_id,
                body=existing_event
            ).execute()
            
            print(f"✅ Event updated: {event_id}")
            return True
            
        except HttpError as error:
            print(f"❌ Error updating event: {error}")
            return False
    
    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """Delete an event"""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            print(f"✅ Event deleted: {event_id}")
            return True
            
        except HttpError as error:
            print(f"❌ Error deleting event: {error}")
            return False
    
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
        self.working_hours = (9, 17)  # 9 AM to 5 PM
        self.break_duration = 15  # minutes between meetings
        
    def find_free_slots(self, 
                       start_date: datetime,
                       end_date: datetime,
                       duration_minutes: int,
                       calendars: List[str] = None) -> List[Tuple[datetime, datetime]]:
        """Find available time slots across multiple calendars"""
        
        if not calendars:
            calendars = ["primary"]
        
        # Ensure timezone awareness
        if start_date.tzinfo is None:
            start_date = self.calendar_manager.default_timezone.localize(start_date)
        if end_date.tzinfo is None:
            end_date = self.calendar_manager.default_timezone.localize(end_date)
        
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
            # Parse event times and ensure timezone awareness
            start_str = event['start']
            end_str = event['end']
            
            # Handle both date-only and datetime events
            if 'T' in start_str:
                event_start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                # Convert to local timezone if needed
                if event_start.tzinfo is None:
                    event_start = self.calendar_manager.default_timezone.localize(event_start)
                if event_end.tzinfo is None:
                    event_end = self.calendar_manager.default_timezone.localize(event_end)
            else:
                # All-day events
                event_start = datetime.strptime(start_str, '%Y-%m-%d')
                event_start = self.calendar_manager.default_timezone.localize(event_start)
                event_end = datetime.strptime(end_str, '%Y-%m-%d')
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
                # Parse event times and ensure timezone awareness
                start_str = existing_event['start']
                end_str = existing_event['end']
                
                # Handle both date-only and datetime events
                if 'T' in start_str:
                    existing_start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    existing_end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    
                    # Convert to local timezone if needed
                    if existing_start.tzinfo is None:
                        existing_start = self.calendar_manager.default_timezone.localize(existing_start)
                    if existing_end.tzinfo is None:
                        existing_end = self.calendar_manager.default_timezone.localize(existing_end)
                else:
                    # All-day events
                    existing_start = datetime.strptime(start_str, '%Y-%m-%d')
                    existing_start = self.calendar_manager.default_timezone.localize(existing_start)
                    existing_end = datetime.strptime(end_str, '%Y-%m-%d')
                    existing_end = self.calendar_manager.default_timezone.localize(existing_end)
                
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
        
        # Initialize Gemini
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for AI Calendar Assistant functionality")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
    
    def parse_natural_language_command(self, command: str) -> Dict[str, Any]:
        """Parse natural language commands using Gemini"""
        
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
                    temperature=0.1,
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
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute natural language calendar command"""
        
        print(f"🤖 Processing: {command}")
        
        # Parse the command
        parsed = self.parse_natural_language_command(command)
        
        if not parsed:
            return {"success": False, "message": "Could not understand the command"}
        
        action = parsed.get('action', '').lower()
        
        try:
            if action == 'create':
                return self._create_event_from_parsed(parsed)
            elif action == 'find':
                return self._find_free_time_from_parsed(parsed)
            elif action == 'list':
                return self._list_events_from_parsed(parsed)
            elif action == 'update':
                return self._update_event_from_parsed(parsed)
            elif action == 'delete':
                return self._delete_event_from_parsed(parsed)
            else:
                return {"success": False, "message": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "message": f"Error executing command: {e}"}
    
    def _create_event_from_parsed(self, parsed: Dict) -> Dict[str, Any]:
        """Create event from parsed natural language"""
        
        # Parse date and time
        event_date = parsed.get('date', datetime.now().strftime('%Y-%m-%d'))
        start_time = parsed.get('start_time', '09:00')
        
        # Calculate end time
        if parsed.get('end_time'):
            end_time = parsed.get('end_time')
        elif parsed.get('duration_minutes'):
            duration = timedelta(minutes=parsed.get('duration_minutes'))
            start_dt = datetime.strptime(f"{event_date} {start_time}", '%Y-%m-%d %H:%M')
            end_dt = start_dt + duration
            end_time = end_dt.strftime('%H:%M')
        else:
            # Default 1 hour duration
            start_dt = datetime.strptime(f"{event_date} {start_time}", '%Y-%m-%d %H:%M')
            end_dt = start_dt + timedelta(hours=1)
            end_time = end_dt.strftime('%H:%M')
        
        # Create datetime objects
        start_datetime = self.calendar_manager.default_timezone.localize(
            datetime.strptime(f"{event_date} {start_time}", '%Y-%m-%d %H:%M')
        )
        end_datetime = self.calendar_manager.default_timezone.localize(
            datetime.strptime(f"{event_date} {end_time}", '%Y-%m-%d %H:%M')
        )
        
        # Create event object
        event = CalendarEvent(
            summary=parsed.get('title', 'Untitled Event'),
            description=parsed.get('description', ''),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=parsed.get('location', ''),
            attendees=parsed.get('attendees', []),
            timezone=parsed.get('timezone', settings.DEFAULT_TIMEZONE)
        )
        
        # Add reminders
        if parsed.get('reminders'):
            event.reminders = [{'method': 'email', 'minutes': minutes} 
                             for minutes in parsed.get('reminders')]
        
        # Add recurrence
        recurrence = parsed.get('recurrence', '').lower()
        if recurrence and recurrence != 'none':
            if recurrence == 'daily':
                event.recurrence = ['RRULE:FREQ=DAILY']
            elif recurrence == 'weekly':
                event.recurrence = ['RRULE:FREQ=WEEKLY']
            elif recurrence == 'monthly':
                event.recurrence = ['RRULE:FREQ=MONTHLY']
            elif recurrence == 'yearly':
                event.recurrence = ['RRULE:FREQ=YEARLY']
        
        # Check for conflicts
        conflicts = self.scheduler.detect_conflicts(event)
        
        if conflicts:
            # Suggest alternatives
            alternatives = self.scheduler.suggest_alternatives(event)
            
            return {
                "success": False,
                "message": "Scheduling conflict detected",
                "conflicts": conflicts,
                "alternatives": [
                    {
                        "start": alt.start_datetime.isoformat(),
                        "end": alt.end_datetime.isoformat(),
                        "start_formatted": alt.start_datetime.strftime('%Y-%m-%d %H:%M'),
                        "end_formatted": alt.end_datetime.strftime('%Y-%m-%d %H:%M')
                    } for alt in alternatives
                ]
            }
        
        # Create the event
        event_id = self.calendar_manager.create_event(event)
        
        if event_id:
            return {
                "success": True,
                "message": f"Event '{event.summary}' created successfully",
                "event_id": event_id,
                "event_details": {
                    "title": event.summary,
                    "start": start_datetime.strftime('%Y-%m-%d %H:%M'),
                    "end": end_datetime.strftime('%Y-%m-%d %H:%M'),
                    "location": event.location,
                    "attendees": event.attendees
                }
            }
        else:
            return {"success": False, "message": "Failed to create event"}
    
    def _find_free_time_from_parsed(self, parsed: Dict) -> Dict[str, Any]:
        """Find free time slots based on parsed command"""
        
        duration_minutes = parsed.get('duration_minutes', 60)
        
        # Default to next 7 days
        start_date = datetime.now(self.calendar_manager.default_timezone)
        end_date = start_date + timedelta(days=7)
        
        # Override if specific date mentioned
        if parsed.get('date'):
            try:
                specific_date = datetime.strptime(parsed['date'], '%Y-%m-%d')
                start_date = self.calendar_manager.default_timezone.localize(
                    specific_date.replace(hour=9, minute=0)
                )
                end_date = start_date.replace(hour=17, minute=0)
            except ValueError:
                pass
        
        free_slots = self.scheduler.find_free_slots(start_date, end_date, duration_minutes)
        
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
            "message": f"Found {len(formatted_slots)} available slots",
            "free_slots": formatted_slots,
            "duration_requested": duration_minutes
        }
    
    def _list_events_from_parsed(self, parsed: Dict) -> Dict[str, Any]:
        """List events based on parsed command"""
        
        # Default to today
        start_date = datetime.now(self.calendar_manager.default_timezone).replace(hour=0, minute=0)
        end_date = start_date + timedelta(days=1)
        
        # Override if specific date mentioned
        if parsed.get('date'):
            try:
                specific_date = datetime.strptime(parsed['date'], '%Y-%m-%d')
                start_date = self.calendar_manager.default_timezone.localize(specific_date)
                end_date = start_date + timedelta(days=1)
            except ValueError:
                pass
        
        events = self.calendar_manager.get_events(start_date, end_date)
        
        formatted_events = []
        for event in events:
            # Parse event times and ensure timezone awareness
            start_str = event['start']
            end_str = event['end']
            
            # Handle both date-only and datetime events
            if 'T' in start_str:
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                # Convert to local timezone if needed
                if start_dt.tzinfo is None:
                    start_dt = self.calendar_manager.default_timezone.localize(start_dt)
                if end_dt.tzinfo is None:
                    end_dt = self.calendar_manager.default_timezone.localize(end_dt)
            else:
                # All-day events
                start_dt = datetime.strptime(start_str, '%Y-%m-%d')
                start_dt = self.calendar_manager.default_timezone.localize(start_dt)
                end_dt = datetime.strptime(end_str, '%Y-%m-%d')
                end_dt = self.calendar_manager.default_timezone.localize(end_dt)
            
            formatted_events.append({
                "id": event['id'],
                "title": event['summary'],
                "start": start_dt.strftime('%I:%M %p'),
                "end": end_dt.strftime('%I:%M %p'),
                "location": event.get('location', ''),
                "attendees_count": len(event.get('attendees', [])),
                "description": event.get('description', '')[:100] + '...' if len(event.get('description', '')) > 100 else event.get('description', '')
            })
        
        return {
            "success": True,
            "message": f"Found {len(formatted_events)} events",
            "events": formatted_events,
            "date": start_date.strftime('%Y-%m-%d')
        }
    
    def _update_event_from_parsed(self, parsed: Dict) -> Dict[str, Any]:
        """Update event based on parsed command"""
        # Implementation for updating events
        return {"success": False, "message": "Update functionality not yet implemented"}
    
    def _delete_event_from_parsed(self, parsed: Dict) -> Dict[str, Any]:
        """Delete event based on parsed command"""
        # Implementation for deleting events
        return {"success": False, "message": "Delete functionality not yet implemented"}
    
    def summarize_meeting_notes(self, meeting_notes: str) -> Dict[str, Any]:
        """Summarize meeting notes and extract action items using Gemini"""
        
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


class CalendarSync:
    """Multi-calendar synchronization utility"""
    
    def __init__(self, calendar_manager: GoogleCalendarManager):
        self.calendar_manager = calendar_manager
    
    def sync_calendars(self, source_calendar_id: str, target_calendar_ids: List[str]) -> Dict[str, Any]:
        """Sync events from source calendar to target calendars"""
        try:
            # Get events from source calendar
            source_events = self.calendar_manager.get_events(calendar_id=source_calendar_id)
            
            sync_results = {
                'success': True,
                'source_calendar': source_calendar_id,
                'target_calendars': target_calendar_ids,
                'synced_events': 0,
                'errors': []
            }
            
            for event in source_events:
                # Parse event times and ensure timezone awareness
                start_str = event['start']
                end_str = event['end']
                
                # Handle both date-only and datetime events
                if 'T' in start_str:
                    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    
                    # Convert to local timezone if needed
                    if start_dt.tzinfo is None:
                        start_dt = self.calendar_manager.default_timezone.localize(start_dt)
                    if end_dt.tzinfo is None:
                        end_dt = self.calendar_manager.default_timezone.localize(end_dt)
                else:
                    # All-day events
                    start_dt = datetime.strptime(start_str, '%Y-%m-%d')
                    start_dt = self.calendar_manager.default_timezone.localize(start_dt)
                    end_dt = datetime.strptime(end_str, '%Y-%m-%d')
                    end_dt = self.calendar_manager.default_timezone.localize(end_dt)
                
                # Create event object
                calendar_event = CalendarEvent(
                    summary=f"[SYNCED] {event['summary']}",
                    description=event.get('description', ''),
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    location=event.get('location', ''),
                    attendees=event.get('attendees', [])
                )
                
                # Sync to each target calendar
                for target_id in target_calendar_ids:
                    calendar_event.calendar_id = target_id
                    event_id = self.calendar_manager.create_event(calendar_event)
                    
                    if event_id:
                        sync_results['synced_events'] += 1
                    else:
                        sync_results['errors'].append(f"Failed to sync event '{event['summary']}' to {target_id}")
            
            return sync_results
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Sync failed: {e}",
                'errors': [str(e)]
            }

class TimeZoneHandler:
    """Handle multiple time zones for international meetings"""
    
    @staticmethod
    def convert_to_timezone(dt: datetime, target_timezone: str) -> datetime:
        """Convert datetime to target timezone"""
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        target_tz = pytz.timezone(target_timezone)
        return dt.astimezone(target_tz)
    
    @staticmethod
    def find_optimal_meeting_time(participant_timezones: List[str], 
                                 working_hours: Tuple[int, int] = (9, 17)) -> List[Dict]:
        """Find optimal meeting times across multiple time zones"""
        optimal_times = []
        
        # Check each hour of the day
        for hour in range(24):
            suitable_for_all = True
            time_info = []
            
            for tz_name in participant_timezones:
                tz = pytz.timezone(tz_name)
                local_time = datetime.now(tz).replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # Check if within working hours
                if not (working_hours[0] <= local_time.hour < working_hours[1]):
                    suitable_for_all = False
                
                time_info.append({
                    'timezone': tz_name,
                    'local_time': local_time.strftime('%H:%M'),
                    'suitable': working_hours[0] <= local_time.hour < working_hours[1]
                })
            
            if suitable_for_all:
                optimal_times.append({
                    'utc_hour': hour,
                    'timezone_info': time_info,
                    'suitability_score': sum(1 for info in time_info if info['suitable'])
                })
        
        # Sort by suitability score
        optimal_times.sort(key=lambda x: x['suitability_score'], reverse=True)
        
        return optimal_times[:5]  # Return top 5 optimal times

class RecurringEventManager:
    """Advanced recurring event management"""
    
    def __init__(self, calendar_manager: GoogleCalendarManager):
        self.calendar_manager = calendar_manager
    
    def create_recurring_event(self, 
                             base_event: CalendarEvent,
                             recurrence_pattern: str,
                             end_date: datetime = None,
                             occurrence_count: int = None) -> Optional[str]:
        """Create recurring event with advanced patterns"""
        
        # Build recurrence rule
        rrule_parts = [f"FREQ={recurrence_pattern.upper()}"]
        
        if end_date:
            rrule_parts.append(f"UNTIL={end_date.strftime('%Y%m%dT%H%M%SZ')}")
        elif occurrence_count:
            rrule_parts.append(f"COUNT={occurrence_count}")
        
        base_event.recurrence = [f"RRULE:{';'.join(rrule_parts)}"]
        
        return self.calendar_manager.create_event(base_event)
    
    def modify_recurring_series(self, 
                              event_id: str, 
                              modification_type: str,
                              **kwargs) -> bool:
        """Modify recurring event series"""
        
        if modification_type == "cancel_single":
            # Cancel single occurrence
            pass
        elif modification_type == "modify_future":
            # Modify this and future occurrences
            pass
        elif modification_type == "modify_all":
            # Modify entire series
            pass
        
        # Implementation would depend on specific requirements
        return True


def main():
    """Example usage of the calendar system"""
    try:
        # Initialize calendar manager
        calendar_manager = GoogleCalendarManager()
        
        # Authenticate with Google Calendar
        if not calendar_manager.authenticate():
            print("❌ Failed to authenticate with Google Calendar")
            return
        
        # Initialize scheduler
        scheduler = SmartScheduler(calendar_manager)
        
        # Initialize AI assistant
        try:
            ai_assistant = AICalendarAssistant(calendar_manager, scheduler)
            print("✅ AI Calendar Assistant initialized successfully")
        except ValueError as e:
            print(f"⚠️ AI Assistant not available: {e}")
            ai_assistant = None
        
        # Example: Create a simple event
        event = CalendarEvent(
            summary="Test Meeting",
            description="This is a test meeting",
            start_datetime=datetime.now(calendar_manager.default_timezone) + timedelta(hours=1),
            end_datetime=datetime.now(calendar_manager.default_timezone) + timedelta(hours=2),
            location="Conference Room A",
            attendees=["test@example.com"]
        )
        
        # Create the event
        event_id = calendar_manager.create_event(event)
        if event_id:
            print(f"✅ Test event created with ID: {event_id}")
        
        # Example: Use AI assistant if available
        if ai_assistant:
            result = ai_assistant.execute_command("Find free time for 1 hour meeting tomorrow")
            print(f"🤖 AI Response: {result}")
        
    except Exception as e:
        print(f"❌ Error in main: {e}")


if __name__ == "__main__":
    main()

