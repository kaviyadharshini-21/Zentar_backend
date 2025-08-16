#!/usr/bin/env python3
"""
Startup script for Zentar Email Backend API
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting Zentar Email Backend API...")
    print(f"📡 Server will be available at: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
