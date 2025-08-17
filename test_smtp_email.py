#!/usr/bin/env python3
"""
Test script for the SMTP Email Service
This script demonstrates how to use the EmailService to send emails via SMTP.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mock the settings for testing
class MockSettings:
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your-email@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your-app-password")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() == "true"

# Mock the config
import sys
sys.path.append('app')
sys.modules['app.config'] = type('MockConfig', (), {'settings': MockSettings})()

async def test_smtp_email_sending():
    """Test the SMTP email sending functionality"""
    
    try:
        from app.services.email_service import EmailService
        from app.schemas.email import EmailCreate
        
        # Initialize the service
        email_service = EmailService()
        
        print("✅ Email service initialized successfully!")
        
        # Check SMTP configuration
        print(f"📧 SMTP Configuration:")
        print(f"   Server: {MockSettings.SMTP_SERVER}")
        print(f"   Port: {MockSettings.SMTP_PORT}")
        print(f"   Username: {MockSettings.SMTP_USERNAME}")
        print(f"   Use TLS: {MockSettings.SMTP_USE_TLS}")
        print()
        
        if MockSettings.SMTP_USERNAME == "your-email@gmail.com":
            print("⚠️  Warning: Please set your actual SMTP credentials in .env file:")
            print("   SMTP_USERNAME=your-actual-email@gmail.com")
            print("   SMTP_PASSWORD=your-app-password")
            print()
            return
        
        # Test 1: Send email via SMTP
        print("📧 Test 1: Send email via SMTP")
        print("=" * 50)
        
        # Create email data
        email_data = EmailCreate(
            to_users=["recipient@example.com"],  # Replace with actual email
            subject="Test Email from Zentar Backend",
            body="This is a test email sent via SMTP from the Zentar Backend application.",
            attachments=[]
        )
        
        # Note: This will require actual SMTP credentials and a real recipient email
        print("📝 Email data prepared:")
        print(f"   To: {email_data.to_users}")
        print(f"   Subject: {email_data.subject}")
        print(f"   Body: {email_data.body}")
        print()
        print("ℹ️  To actually send the email, you need:")
        print("   1. Valid SMTP credentials in your .env file")
        print("   2. A real recipient email address")
        print("   3. Uncomment the send_email_via_smtp call below")
        print()
        
        # Uncomment the following lines to actually send the email
        # result = await email_service.send_email_via_smtp("mock_user_id", email_data)
        # if result["success"]:
        #     print("✅ Email sent successfully via SMTP!")
        #     print(f"   Message: {result['message']}")
        #     print(f"   Email ID: {result['email_id']}")
        #     print(f"   Recipients: {result['recipients']}")
        # else:
        #     print(f"❌ Failed to send email: {result.get('error', 'Unknown error')}")
        
        # Test 2: Send bulk email via SMTP
        print("📧 Test 2: Send bulk email via SMTP")
        print("=" * 50)
        
        recipient_emails = [
            "recipient1@example.com",
            "recipient2@example.com",
            "recipient3@example.com"
        ]
        
        print("📝 Bulk email data prepared:")
        print(f"   Recipients: {recipient_emails}")
        print(f"   Subject: {email_data.subject}")
        print(f"   Body: {email_data.body}")
        print()
        print("ℹ️  To actually send bulk emails, uncomment the send_bulk_email_via_smtp call below")
        print()
        
        # Uncomment the following lines to actually send bulk emails
        # result = await email_service.send_bulk_email_via_smtp("mock_user_id", email_data, recipient_emails)
        # if result["success"]:
        #     print("✅ Bulk emails sent successfully via SMTP!")
        #     print(f"   Message: {result['message']}")
        #     print(f"   Total sent: {result['total_sent']}")
        #     print(f"   Recipients: {result['recipients']}")
        # else:
        #     print(f"❌ Failed to send bulk emails: {result.get('error', 'Unknown error')}")
        
        print("🎉 SMTP email testing completed!")
        print()
        print("📋 Next steps:")
        print("   1. Set your SMTP credentials in .env file")
        print("   2. Replace recipient emails with real addresses")
        print("   3. Uncomment the email sending calls above")
        print("   4. Run the script again to actually send emails")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have all required dependencies installed:")
        print("pip install python-dotenv")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🚀 Testing SMTP Email Service")
    print("=" * 50)
    
    # Check if SMTP credentials are set
    if not os.getenv("SMTP_USERNAME") or not os.getenv("SMTP_PASSWORD"):
        print("⚠️  Warning: SMTP credentials not found in environment variables")
        print("   Create a .env file with your SMTP credentials:")
        print("   SMTP_USERNAME=your-email@gmail.com")
        print("   SMTP_PASSWORD=your-app-password")
        print("   SMTP_SERVER=smtp.gmail.com")
        print("   SMTP_PORT=587")
        print("   SMTP_USE_TLS=True")
        print()
    
    # Run the tests
    asyncio.run(test_smtp_email_sending())
