#!/usr/bin/env python3
"""
Test script for the AI Email Composition Service
This script demonstrates how to use the EmailService to compose emails using Gemini AI.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mock the settings for testing
class MockSettings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")

# Mock the config
import sys
sys.path.append('app')
sys.modules['app.config'] = type('MockConfig', (), {'settings': MockSettings})()

async def test_email_composition():
    """Test the email composition service"""
    
    try:
        from app.services.email_service import EmailService
        
        # Initialize the service
        email_service = EmailService()
        
        if not email_service.model:
            print("❌ Gemini AI not configured. Please set GEMINI_API_KEY in your .env file")
            return
        
        print("✅ Email composition service initialized successfully!")
        
        # Test 1: Basic email composition
        print("\n📧 Test 1: Basic email composition")
        print("=" * 50)
        
        result = await email_service.compose_email(
            context="Request a meeting to discuss the new project requirements",
            tone="professional",
            length="medium",
            recipient_type="colleague"
        )
        
        if result["success"]:
            print("✅ Email composed successfully!")
            print(f"Subject: {result['email']['subject']}")
            print(f"Word count: {result['email']['metadata']['word_count']}")
            print("\n📝 Email Content (Markdown):")
            print("-" * 30)
            print(result['email']['content'])
            print("-" * 30)
        else:
            print(f"❌ Failed to compose email: {result['error']}")
        
        # Test 2: Template-based email composition
        print("\n📧 Test 2: Template-based email composition")
        print("=" * 50)
        
        template_context = {
            "recipient_name": "Sarah Johnson",
            "purpose": "Weekly team sync meeting",
            "proposed_time": "Every Monday at 10 AM",
            "duration": "30 minutes",
            "location": "Zoom meeting"
        }
        
        result = await email_service.compose_email_with_template(
            template_type="meeting_request",
            context=template_context
        )
        
        if result["success"]:
            print("✅ Template email composed successfully!")
            print(f"Template used: {result['email']['metadata']['template_used']}")
            print(f"Word count: {result['email']['metadata']['word_count']}")
            print("\n📝 Email Content (Markdown):")
            print("-" * 30)
            print(result['email']['content'])
            print("-" * 30)
        else:
            print(f"❌ Failed to compose template email: {result['error']}")
        
        # Test 3: Different tone and length
        print("\n📧 Test 3: Friendly short email")
        print("=" * 50)
        
        result = await email_service.compose_email(
            context="Thank you for helping me with the presentation yesterday",
            tone="friendly",
            length="short",
            recipient_type="friend"
        )
        
        if result["success"]:
            print("✅ Friendly short email composed successfully!")
            print(f"Tone: {result['email']['metadata']['tone']}")
            print(f"Length: {result['email']['metadata']['length']}")
            print(f"Word count: {result['email']['metadata']['word_count']}")
            print("\n📝 Email Content (Markdown):")
            print("-" * 30)
            print(result['email']['content'])
            print("-" * 30)
        else:
            print(f"❌ Failed to compose friendly email: {result['error']}")
        
        # Test 4: Persuasive long email
        print("\n📧 Test 4: Persuasive long email")
        print("=" * 50)
        
        result = await email_service.compose_email(
            context="Propose a new initiative to improve team productivity through better communication tools",
            tone="persuasive",
            length="long",
            recipient_type="manager"
        )
        
        if result["success"]:
            print("✅ Persuasive long email composed successfully!")
            print(f"Tone: {result['email']['metadata']['tone']}")
            print(f"Length: {result['email']['metadata']['length']}")
            print(f"Word count: {result['email']['metadata']['word_count']}")
            print("\n📝 Email Content (Markdown):")
            print("-" * 30)
            print(result['email']['content'])
            print("-" * 30)
        else:
            print(f"❌ Failed to compose persuasive email: {result['error']}")
        
        print("\n🎉 All tests completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have all required dependencies installed:")
        print("pip install google-generativeai python-dotenv")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🚀 Testing AI Email Composition Service")
    print("=" * 50)
    
    # Check if Gemini API key is set
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not found in environment variables")
        print("   Create a .env file with your Gemini API key:")
        print("   GEMINI_API_KEY=your-actual-api-key-here")
        print()
    
    # Run the tests
    asyncio.run(test_email_composition())
