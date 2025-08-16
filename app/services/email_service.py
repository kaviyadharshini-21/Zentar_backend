from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from app.models.email import Email
from app.models.thread import Thread
from app.models.user import User
from app.schemas.email import EmailCreate, EmailResponse, EmailUpdate, EmailListResponse
from app.schemas.thread import ThreadResponse
from bson import ObjectId
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from app.config import settings

def fetch_latest_10_emails():
    try:
        # Check if IMAP settings are configured
        if not settings.IMAP_SERVER or not settings.IMAP_USERNAME or not settings.IMAP_PASSWORD:
            print("IMAP settings not configured, returning empty list")
            return []
            
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(settings.IMAP_SERVER)
        mail.login(settings.IMAP_USERNAME, settings.IMAP_PASSWORD)

        # Select inbox
        mail.select("inbox")

        # Search all emails
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()

        # Get last 10 email IDs
        latest_ids = email_ids[-10:]

        emails = []
        for num in reversed(latest_ids):
            status, data = mail.fetch(num, "(RFC822)")
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decode subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")

            # Decode sender
            from_, encoding = decode_header(msg.get("From"))[0]
            if isinstance(from_, bytes):
                from_ = from_.decode(encoding if encoding else "utf-8")

            # Decode recipient (To field)
            to_field = msg.get("To", "")
            to_encoding = decode_header(to_field)[0][1] if to_field else None
            if isinstance(to_field, bytes):
                to_field = to_field.decode(to_encoding if to_encoding else "utf-8")

            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            # Get date
            date_str = msg.get("Date", "")
            try:
                from email.utils import parsedate_to_datetime
                sent_at = parsedate_to_datetime(date_str)
            except:
                sent_at = datetime.now()

            # Get attachments
            attachments = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_filename():
                        filename = part.get_filename()
                        if isinstance(filename, bytes):
                            filename = filename.decode()
                        attachments.append(filename)

            emails.append({
                "id": num.decode() if isinstance(num, bytes) else str(num),
                "from_user": from_,
                "to_users": [to_field] if to_field else [],
                "subject": subject,
                "body": body,
                "threadId": f"thread_{num.decode() if isinstance(num, bytes) else str(num)}",
                "isRead": False,
                "isDeleted": False,
                "sentAt": sent_at,
                "attachments": attachments
            })


        mail.logout()
        return emails
    except Exception as e:
        print(f"Error fetching emails from IMAP: {str(e)}")
        return []

class EmailService:
    @staticmethod
    async def get_inbox_emails(user_id: str, page: int = 1, limit: int = 20) -> EmailListResponse:
        """Get inbox emails for a user"""
        try:
            skip = (page - 1) * limit
            
            # Find emails where user is in the 'to' list and not deleted
            emails = fetch_latest_10_emails()
            # Get total count from fetched emails
            total = len(emails)
            # Convert to response format
            email_responses = []
            for email in emails:
                email_responses.append(EmailResponse(
                    id=str(email["id"]),
                    from_user=str(email["from_user"]),
                    to_users=[str(to_id) for to_id in email["to_users"]],
                    subject=email["subject"],
                    body=email["body"],
                    threadId=str(email["threadId"]),
                    isRead=email["isRead"],
                    isDeleted=email["isDeleted"],
                    sentAt=email["sentAt"],
                    attachments=email["attachments"]
                ))
            print(email_responses)
            return EmailListResponse(
                emails=email_responses,
                total=total,
                page=page,
                limit=limit
            )
        except Exception as e:
            import logging
            logging.error(f"Error fetching inbox emails for user {user_id}: {str(e)}")
            logging.error(f"Exception type: {type(e).__name__}")
            logging.error(f"Exception details: {e}")
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching inbox emails: {str(e)}"
            )

    @staticmethod
    async def get_thread_emails(thread_id: str, user_id: str) -> List[EmailResponse]:
        """Get all emails in a thread"""
        try:
            # Verify user has access to this thread
            thread = await Thread.get(ObjectId(thread_id))
            if not thread or ObjectId(user_id) not in thread.participants:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this thread"
                )
            
            # Get all emails in the thread
            emails = await Email.find({"threadId": ObjectId(thread_id)}).sort([("sentAt", 1)]).to_list()
            
            email_responses = []
            for email in emails:
                email_responses.append(EmailResponse(
                    id=str(email.id),
                    from_user=str(email.from_user),
                    to_users=[str(to_id) for to_id in email.to_users],
                    subject=email.subject,
                    body=email.body,
                    threadId=str(email.threadId),
                    isRead=email.isRead,
                    isDeleted=email.isDeleted,
                    sentAt=email.sentAt,
                    attachments=email.attachments
                ))
            
            return email_responses
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching thread emails: {str(e)}"
            )

    @staticmethod
    async def send_email(user_id: str, email_data: EmailCreate) -> EmailResponse:
        """Send a new email"""
        try:
            # Convert string IDs to ObjectIds
            to_user_ids = [ObjectId(user_id_str) for user_id_str in email_data.to_users]
            
            # Verify all recipients exist
            for user_id_str in email_data.to_users:
                recipient = await User.get(ObjectId(user_id_str))
                if not recipient:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Recipient with ID {user_id_str} not found"
                    )
            
            # Find or create thread
            thread = await Thread.find_one({
                "participants": {"$all": [ObjectId(user_id)] + to_user_ids}
            })
            
            if not thread:
                # Create new thread
                thread = Thread(participants=[ObjectId(user_id)] + to_user_ids)
                await thread.insert()
            
            # Create email
            email = Email(
                from_user=ObjectId(user_id),
                to_users=to_user_ids,
                subject=email_data.subject,
                body=email_data.body,
                threadId=thread.id,
                attachments=email_data.attachments or []
            )
            
            await email.insert()
            
            # Update thread with new email
            await thread.update({"$push": {"emails": email.id}, "$set": {"lastUpdated": datetime.now()}})
            
            return EmailResponse(
                id=str(email.id),
                from_user=str(email.from_user),
                to_users=[str(to_id) for to_id in email.to_users],
                subject=email.subject,
                body=email.body,
                threadId=str(email.threadId),
                isRead=email.isRead,
                isDeleted=email.isDeleted,
                sentAt=email.sentAt,
                attachments=email.attachments
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error sending email: {str(e)}"
            )

    @staticmethod
    async def mark_email_read(email_id: str, user_id: str) -> EmailResponse:
        """Mark an email as read"""
        try:
            email = await Email.get(ObjectId(email_id))
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email not found"
                )
            
            # Verify user has access to this email
            if ObjectId(user_id) not in email.to_users:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this email"
                )
            
            # Mark as read
            await email.update({"$set": {"isRead": True}})
            
            return EmailResponse(
                id=str(email.id),
                from_user=str(email.from_user),
                to_users=[str(to_id) for to_id in email.to_users],
                subject=email.subject,
                body=email.body,
                threadId=str(email.threadId),
                isRead=True,
                isDeleted=email.isDeleted,
                sentAt=email.sentAt,
                attachments=email.attachments
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error marking email as read: {str(e)}"
            )

    @staticmethod
    async def delete_email(email_id: str, user_id: str) -> bool:
        """Delete an email (soft delete)"""
        try:
            email = await Email.get(ObjectId(email_id))
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email not found"
                )
            
            # Verify user has access to this email
            if ObjectId(user_id) not in email.to_users and ObjectId(user_id) != email.from_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this email"
                )
            
            # Soft delete
            await email.update({"$set": {"isDeleted": True}})
            
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting email: {str(e)}"
            )