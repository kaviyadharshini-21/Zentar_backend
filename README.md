# Zentar Email Backend API

A FastAPI backend for email management with reminders and meetings, built with MongoDB and JWT authentication. Now featuring **AI-powered meeting management** with Google Calendar integration and Gemini AI capabilities.

## 🚀 Features

- **User Authentication**: JWT-based authentication with secure password hashing
- **Email Management**: Send, receive, and manage emails with threading
- **Reminders**: Set reminders for emails with scheduled notifications
- **Meeting Scheduling**: Create and manage meetings with participants
- **🤖 AI-Powered Meeting Management**: 
  - Natural language meeting commands
  - Smart scheduling with conflict detection
  - AI-powered meeting notes analysis
  - Google Calendar integration
  - Free time slot detection
- **User Settings**: Customizable user preferences and settings
- **RESTful API**: Clean, documented API endpoints
- **MongoDB Integration**: Using Motor and Beanie for async MongoDB operations

## 🛠️ Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **MongoDB**: NoSQL database with Motor for async operations
- **Beanie**: ODM for MongoDB with Pydantic integration
- **JWT**: JSON Web Tokens for authentication
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server for running FastAPI
- **Google Calendar API**: Calendar integration and sync
- **Google Gemini AI**: Natural language processing and meeting analysis
- **Pytz**: Timezone handling and management

## 📋 Prerequisites

- Python 3.8+
- MongoDB (local or cloud instance)
- pip (Python package manager)
- Google Cloud Platform account (for Calendar API)
- Google AI Studio account (for Gemini API)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Zentar_backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env with your configuration
   ```

5. **Configure MongoDB**
   - Ensure MongoDB is running locally or update the `MONGODB_URL` in your `.env` file
   - The database will be created automatically on first run

6. **Set up Google Calendar API** (Optional)
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Calendar API
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Choose "Desktop application" as application type
   - Download the `credentials.json` file
   - Place it in your project root directory
   - Set `GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json` in your `.env` file

7. **Set up Gemini AI** (Optional)
   - Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Add it to your `.env` file as `GEMINI_API_KEY`

8. **Run the application**
   ```bash
   python -m app.main
   ```

   Or using uvicorn directly:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 📚 API Documentation

Once the server is running, you can access:

- **Interactive API Docs**: http://localhost:8000/docs

## 🔧 Troubleshooting

### Google Calendar Issues
- **"Credentials file not found"**: Make sure `credentials.json` is in your project root
- **"Authentication failed"**: Check that your Google Cloud project has Calendar API enabled
- **"Access denied"**: Ensure your OAuth consent screen is configured properly

### Database Issues
- **"Connection refused"**: Make sure MongoDB is running and accessible
- **"Authentication failed"**: Check your MongoDB connection string in `.env`

### General Issues
- **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`
- **Port conflicts**: Change the port in `.env` if 8000 is already in use
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🤖 AI Meeting Management

The new AI-powered meeting management system includes:

### Natural Language Commands
```bash
# Schedule meetings using natural language
POST /api/v1/meetings/ai/command
{
  "command": "Schedule meeting tomorrow at 2 PM with john@example.com"
}
```

### Meeting Notes Analysis
```bash
# Analyze meeting notes with AI
POST /api/v1/meetings/ai/summarize-notes
{
  "notes": "Team standup meeting notes..."
}
```

### Smart Scheduling
```bash
# Find optimal meeting times
POST /api/v1/meetings/ai/find-free-slots
{
  "duration_minutes": 60
}
```

For detailed setup and usage instructions, see [AI_MEETING_SETUP.md](AI_MEETING_SETUP.md).

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication. To access protected endpoints:

1. **Register a user**: `POST /auth/signup`
2. **Login**: `POST /auth/login` (returns JWT token)
3. **Use the token**: Include `Authorization: Bearer <token>` in request headers

## 🔑 Google OAuth Credentials

To use Google OAuth for email functionality, you need to set up credentials:

1. Create a `credentials.json` file in the root directory
2. Add your Google OAuth credentials in the following format:

```json
{
  "installed": {
    "client_id": "YOUR_GOOGLE_CLIENT_ID_HERE",
    "project_id": "YOUR_GOOGLE_PROJECT_ID_HERE",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_GOOGLE_CLIENT_SECRET_HERE",
    "redirect_uris": ["http://localhost"]
  }
}
```

**⚠️ Important:** Never commit your actual credentials to version control. The `credentials.json` file is already in `.gitignore`.

## 📡 API Endpoints

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/profile` - Get current user profile
- `PUT /auth/profile` - Update user profile
- `POST /auth/logout` - Logout user

### Emails
- `GET /emails/inbox` - Get inbox emails
- `GET /emails/thread/{thread_id}` - Get thread emails
- `POST /emails/send` - Send new email
- `POST /emails/{email_id}/read` - Mark email as read
- `DELETE /emails/{email_id}` - Delete email

### Reminders
- `GET /reminders/` - Get user reminders
- `POST /reminders/` - Create reminder
- `DELETE /reminders/{reminder_id}` - Delete reminder

### Meetings
- `GET /meetings/` - Get user meetings
- `POST /meetings/` - Create meeting
- `GET /meetings/{meeting_id}` - Get meeting details
- `PUT /meetings/{meeting_id}` - Update meeting
- `DELETE /meetings/{meeting_id}` - Cancel meeting

### Settings
- `GET /settings/` - Get user settings
- `PUT /settings/` - Update user settings

## 🔧 Configuration

Update the `.env` file with your configuration:

```env
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=zentar_email

# JWT Configuration
SECRET_KEY=your-secret-key-here-make-it-long-and-secure
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# CORS Configuration
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

## 📊 Database Schema

### User
```json
{
  "_id": "ObjectId",
  "name": "string",
  "email": "string (unique)",
  "password": "string (hashed)",
  "avatar": "string (optional)",
  "settings": "object",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Email
```json
{
  "_id": "ObjectId",
  "from": "ObjectId (User)",
  "to": ["ObjectId (User)"],
  "subject": "string",
  "body": "string",
  "threadId": "ObjectId",
  "isRead": "boolean",
  "isDeleted": "boolean",
  "sentAt": "datetime",
  "attachments": ["string"]
}
```

### Thread
```json
{
  "_id": "ObjectId",
  "participants": ["ObjectId (User)"],
  "emails": ["ObjectId (Email)"],
  "lastUpdated": "datetime"
}
```

### Reminder
```json
{
  "_id": "ObjectId",
  "userId": "ObjectId",
  "emailId": "ObjectId",
  "remindAt": "datetime",
  "createdAt": "datetime"
}
```

### Meeting
```json
{
  "_id": "ObjectId",
  "organizerId": "ObjectId",
  "participants": ["ObjectId"],
  "title": "string",
  "description": "string",
  "startTime": "datetime",
  "endTime": "datetime",
  "status": "string (scheduled|completed|cancelled)"
}
```

## 🧪 Testing

The API includes comprehensive error handling and validation. You can test endpoints using:

1. **Interactive docs**: Visit http://localhost:8000/docs
2. **Postman**: Import the API endpoints
3. **curl**: Use command line tools

### Example API Calls

**Register a user:**
```bash
curl -X POST "http://localhost:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "password123"
  }'
```

**Login:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'
```

**Send an email (with token):**
```bash
curl -X POST "http://localhost:8000/emails/send" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_users": ["user_id_here"],
    "subject": "Hello",
    "body": "This is a test email"
  }'
```

## 🚀 Deployment

### Docker (Recommended)

1. **Build the image:**
   ```bash
   docker build -t zentar-backend .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8000:8000 --env-file .env zentar-backend
   ```

### Production Considerations

- Use a production ASGI server like Gunicorn with Uvicorn workers
- Set up proper MongoDB authentication and network security
- Use environment variables for sensitive configuration
- Set up proper logging and monitoring
- Configure CORS for your production domains
- Use HTTPS in production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the code comments
- Open an issue on GitHub
