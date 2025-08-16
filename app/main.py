import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db, close_db
from app.routers import auth, emails, reminders, meetings, meeting_ai, settings as settings_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

app = FastAPI(
    title="Zentar Email Backend API",
    description="A FastAPI backend for email management with reminders and meetings",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(emails.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(meeting_ai.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Zentar Email Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

@app.get("/debug/db")
async def debug_database():
    """Debug endpoint to test database connection"""
    try:
        from app.database import init_db
        from app.models.user import User
        import logging
        
        logging.info("Testing database connection...")
        
        # Test if we can connect to MongoDB
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.config import settings
        
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        await client.admin.command('ping')
        
        # Test if we can query users
        user_count = await User.count_documents({})
        
        return {
            "status": "success",
            "mongodb_connection": "OK",
            "database_name": settings.DATABASE_NAME,
            "user_count": user_count,
            "message": "Database connection and query successful"
        }
    except Exception as e:
        import logging
        logging.error(f"Database debug failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "message": "Database connection or query failed"
        }

@app.get("/debug/test")
async def debug_test():
    """Simple test endpoint without authentication"""
    return {
        "status": "success",
        "message": "Basic endpoint working",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
