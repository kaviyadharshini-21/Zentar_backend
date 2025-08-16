# AI-Powered Meeting Management Setup Guide

This guide will help you set up the enhanced AI-powered meeting management system with Google Calendar integration and Gemini AI capabilities.

## Features

- 🤖 **AI-Powered Natural Language Processing**: Schedule meetings using natural language commands
- 📅 **Google Calendar Integration**: Sync meetings with Google Calendar
- ⚡ **Smart Scheduling**: Intelligent conflict detection and alternative time suggestions
- 📝 **Meeting Notes Analysis**: AI-powered meeting summary and action item extraction
- 🕐 **Free Time Detection**: Find optimal meeting slots based on working hours and existing meetings

## Prerequisites

1. Python 3.8+
2. MongoDB database
3. Google Cloud Platform account
4. Google AI Studio account (for Gemini API)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=zentar_email

# JWT Configuration
SECRET_KEY=your-secret-key-here-make-it-long-and-secure
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Calendar API Configuration
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.pickle

# Gemini AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Default Settings
DEFAULT_TIMEZONE=UTC
DEFAULT_MEETING_DURATION=60
BUFFER_TIME_BETWEEN_MEETINGS=15

# AI Assistant Settings
AI_TEMPERATURE=0.1
MAX_ALTERNATIVES_SUGGESTED=3
ENABLE_CONFLICT_DETECTION=True
ENABLE_SMART_SCHEDULING=True
```

## Google Calendar Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Desktop application"
4. Download the credentials file and save it as `credentials.json` in your project root

### 3. Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Add your email as a test user
3. Add the following scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/calendar.events`

## Gemini AI Setup

### 1. Get API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key and add it to your `.env` file as `GEMINI_API_KEY`

## API Endpoints

### AI Meeting Management

#### 1. Process Natural Language Commands

```http
POST /api/v1/meetings/ai/command
Content-Type: application/json

{
  "command": "Schedule meeting tomorrow at 2 PM with john@example.com"
}
```

**Supported Commands:**
- `"Schedule meeting tomorrow at 2 PM with john@example.com"`
- `"Find free time for 1 hour meeting next week"`
- `"Create daily standup at 9 AM starting Monday"`
- `"Delete the meeting with client on Friday"`

#### 2. Summarize Meeting Notes

```http
POST /api/v1/meetings/ai/summarize-notes
Content-Type: application/json

{
  "notes": "Team standup meeting - January 15, 2025\n\nAttendees: John, Sarah, Mike\n\nProgress Updates:\n- Sarah completed the user authentication module\n- Mike finished the dashboard mockups\n\nAction Items:\n- Sarah: Optimize database queries by Thursday\n- Mike: Prepare design presentation for client by Monday"
}
```

**Response includes:**
- Summary
- Action items with assignees
- Key decisions
- Follow-up items

#### 3. Find Free Time Slots

```http
POST /api/v1/meetings/ai/find-free-slots
Content-Type: application/json

{
  "duration_minutes": 60,
  "start_date": "2025-01-20T00:00:00Z",
  "end_date": "2025-01-27T00:00:00Z"
}
```

#### 4. Get Calendar Status

```http
GET /api/v1/meetings/ai/calendar-status
```

#### 5. Suggest Alternative Times

```http
POST /api/v1/meetings/ai/suggest-alternatives
Content-Type: application/json

{
  "meeting_id": "meeting_id_here"
}
```

#### 6. Get Working Hours

```http
GET /api/v1/meetings/ai/working-hours
```

## Usage Examples

### Python Client Example

```python
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Headers with authentication
headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN",
    "Content-Type": "application/json"
}

# 1. Process natural language command
command_data = {
    "command": "Find free time for 1 hour meeting tomorrow"
}
response = requests.post(
    f"{BASE_URL}/meetings/ai/command",
    headers=headers,
    json=command_data
)
print("Free slots:", response.json())

# 2. Summarize meeting notes
notes_data = {
    "notes": """
    Team standup meeting - January 15, 2025
    
    Attendees: John (Project Manager), Sarah (Developer), Mike (Designer)
    
    Progress Updates:
    - Sarah completed the user authentication module
    - Mike finished the dashboard mockups
    
    Action Items:
    - Sarah: Optimize database queries by Thursday
    - Mike: Prepare design presentation for client by Monday
    
    Decisions Made:
    - Move release date to end of February
    - Use PostgreSQL instead of MySQL
    """
}
response = requests.post(
    f"{BASE_URL}/meetings/ai/summarize-notes",
    headers=headers,
    json=notes_data
)
print("Meeting summary:", response.json())
```

### JavaScript/TypeScript Client Example

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';

// Headers with authentication
const headers = {
  'Authorization': 'Bearer YOUR_JWT_TOKEN',
  'Content-Type': 'application/json'
};

// 1. Process natural language command
async function processCommand(command) {
  const response = await fetch(`${BASE_URL}/meetings/ai/command`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ command })
  });
  return response.json();
}

// 2. Summarize meeting notes
async function summarizeNotes(notes) {
  const response = await fetch(`${BASE_URL}/meetings/ai/summarize-notes`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ notes })
  });
  return response.json();
}

// 3. Find free slots
async function findFreeSlots(durationMinutes = 60) {
  const response = await fetch(`${BASE_URL}/meetings/ai/find-free-slots`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ duration_minutes: durationMinutes })
  });
  return response.json();
}

// Usage
processCommand("Schedule meeting tomorrow at 2 PM with john@example.com")
  .then(result => console.log('Command result:', result));

summarizeNotes("Team meeting notes...")
  .then(result => console.log('Summary:', result));
```

## Configuration Options

### Working Hours

Configure working hours in your `.env` file:

```env
DEFAULT_WORKING_HOURS=9,17  # 9 AM to 5 PM
```

### Buffer Time

Set buffer time between meetings:

```env
BUFFER_TIME_BETWEEN_MEETINGS=15  # 15 minutes
```

### AI Temperature

Control AI creativity vs consistency:

```env
AI_TEMPERATURE=0.1  # Lower = more focused, Higher = more creative
```

### Conflict Detection

Enable/disable conflict detection:

```env
ENABLE_CONFLICT_DETECTION=True
```

## Troubleshooting

### Google Calendar Authentication Issues

1. **Credentials file not found**: Ensure `credentials.json` is in your project root
2. **OAuth consent screen**: Add your email as a test user
3. **Scopes**: Ensure calendar scopes are added to OAuth consent screen

### Gemini AI Issues

1. **API key not working**: Verify your API key in Google AI Studio
2. **Rate limiting**: Check your API usage limits
3. **Model not available**: Ensure you're using a supported model

### General Issues

1. **Dependencies**: Run `pip install -r requirements.txt`
2. **Environment variables**: Check your `.env` file configuration
3. **Database connection**: Verify MongoDB is running and accessible

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **OAuth Tokens**: Store tokens securely and refresh when needed
3. **User Permissions**: Implement proper user authentication and authorization
4. **Data Privacy**: Ensure meeting data is handled according to privacy regulations

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the API documentation at `/docs`
3. Check the logs for detailed error messages
4. Ensure all dependencies are properly installed

## License

This project is licensed under the MIT License.
