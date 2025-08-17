import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from app.repositories.email_classification import classify_email
from fastapi import HTTPException, status
from bson import ObjectId
from app.models.email import Email
from app.models.user import User
from app.models.thread import Thread
from app.schemas.email import EmailCreate, EmailResponse, EmailListResponse
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

            category = classify_email(subject,body)
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
                "attachments": attachments,
                "category": category
            })


        mail.logout()
        return emails
    except Exception as e:
        print(f"Error fetching emails from IMAP: {str(e)}")
        return []

class EmailService:
    """Email service with AI-powered composition using Gemini"""
    
    def __init__(self):
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
    
    async def compose_email(self, 
                          context: str, 
                          tone: str = "professional", 
                          length: str = "medium",
                          recipient_type: str = "colleague",
                          subject_line: Optional[str] = None) -> Dict[str, Any]:
        """
        Compose an email using Gemini AI based on user parameters
        
        Args:
            context: The context/purpose of the email
            tone: Email tone (professional, friendly, formal, casual, persuasive)
            length: Email length (short, medium, long)
            recipient_type: Type of recipient (colleague, client, manager, friend)
            subject_line: Optional custom subject line
        
        Returns:
            Dict containing the composed email in markdown format
        """
        try:
            if not self.model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="AI email composition not configured. Please set GEMINI_API_KEY."
                )
            
            # Build the prompt based on user parameters
            prompt = self._build_composition_prompt(context, tone, length, recipient_type, subject_line)
            
            # Generate email content using Gemini
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            # Clean and parse the response
            email_content = response.text.strip()
            
            # Extract subject line if not provided
            if not subject_line:
                subject_line = self._extract_subject_line(email_content)
            
            # Format the response
            return {
                "success": True,
                "email": {
                    "subject": subject_line,
                    "content": email_content,
                    "content_plain": self._markdown_to_plain(email_content),
                    "metadata": {
                        "context": context,
                        "tone": tone,
                        "length": length,
                        "recipient_type": recipient_type,
                        "generated_at": datetime.now().isoformat(),
                        "word_count": len(email_content.split())
                    }
                }
            }
            
        except Exception as e:
            print(f"❌ Error composing email: {e}")
            return {
                "success": False,
                "error": f"Failed to compose email: {str(e)}"
            }
    
    def _build_composition_prompt(self, context: str, tone: str, length: str, recipient_type: str, subject_line: Optional[str]) -> str:
        """Build the prompt for Gemini based on user parameters"""
        
        # Define tone descriptions
        tone_descriptions = {
            "professional": "formal and business-like, using proper business etiquette",
            "friendly": "warm and approachable, maintaining professionalism",
            "formal": "very formal and traditional business communication",
            "casual": "relaxed and conversational, but still respectful",
            "persuasive": "convincing and compelling, using persuasive language"
        }
        
        # Define length guidelines
        length_guidelines = {
            "short": "2-3 sentences, very concise",
            "medium": "4-6 sentences, balanced detail",
            "long": "7-10 sentences, comprehensive coverage"
        }
        
        # Define recipient-specific guidelines
        recipient_guidelines = {
            "colleague": "peer-to-peer communication, collaborative tone",
            "client": "customer-focused, solution-oriented, professional",
            "manager": "respectful, informative, action-oriented",
            "friend": "personal but appropriate for the context"
        }
        
        prompt = f"""
        Compose a professional email based on the following requirements:
        
        CONTEXT: {context}
        TONE: {tone_descriptions.get(tone, tone)} 
        LENGTH: {length_guidelines.get(length, length)}
        RECIPIENT: {recipient_guidelines.get(recipient_type, recipient_type)}
        
        REQUIREMENTS:
        1. Write the email in markdown format
        2. Start with a clear subject line (if not provided)
        3. Use appropriate greeting based on recipient type
        4. Maintain the specified tone throughout
        5. Keep to the specified length
        6. End with an appropriate closing
        7. Make the content relevant and actionable
        
        FORMAT:
        ```markdown
        Subject: [Subject Line]
        
        [Greeting],
        
        [Email Body]
        
        [Closing],
        [Your Name]
        ```
        
        IMPORTANT: Return only the markdown-formatted email content without any additional text or explanations.
        """
        
        if subject_line:
            prompt += f"\n\nUse this exact subject line: {subject_line}"
        
        return prompt
    
    def _extract_subject_line(self, email_content: str) -> str:
        """Extract subject line from the generated email content"""
        try:
            # Look for subject line in the markdown
            lines = email_content.split('\n')
            for line in lines:
                if line.strip().startswith('Subject:'):
                    return line.replace('Subject:', '').strip()
            
            # If no subject found, generate a generic one
            return "Email regarding your request"
        except:
            return "Email regarding your request"
    
    def _markdown_to_plain(self, markdown_content: str) -> str:
        """Convert markdown content to plain text"""
        try:
            # Simple markdown to plain text conversion
            plain_text = markdown_content
            
            # Remove markdown formatting
            plain_text = plain_text.replace('**', '')  # Bold
            plain_text = plain_text.replace('*', '')   # Italic
            plain_text = plain_text.replace('`', '')   # Code
            plain_text = plain_text.replace('#', '')   # Headers
            
            # Clean up extra whitespace
            lines = plain_text.split('\n')
            cleaned_lines = []
            for line in lines:
                cleaned_line = line.strip()
                if cleaned_line:
                    cleaned_lines.append(cleaned_line)
            
            return '\n'.join(cleaned_lines)
        except:
            return markdown_content
    
    async def compose_email_with_template(self, 
                                        template_type: str,
                                        context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compose email using predefined templates
        
        Args:
            template_type: Type of template (meeting_request, follow_up, thank_you, etc.)
            context: Context data for the template
        """
        try:
            if not self.model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="AI email composition not configured. Please set GEMINI_API_KEY."
                )
            
            # Build template-specific prompt
            prompt = self._build_template_prompt(template_type, context)
            
            # Generate email content
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            email_content = response.text.strip()
            
            return {
                "success": True,
                "email": {
                    "subject": context.get('subject', 'Email'),
                    "content": email_content,
                    "content_plain": self._markdown_to_plain(email_content),
                    "template_type": template_type,
                    "metadata": {
                        "template_used": template_type,
                        "generated_at": datetime.now().isoformat(),
                        "word_count": len(email_content.split())
                    }
                }
            }
            
        except Exception as e:
            print(f"❌ Error composing template email: {e}")
            return {
                "success": False,
                "error": f"Failed to compose template email: {str(e)}"
            }
    
    def _build_template_prompt(self, template_type: str, context: Dict[str, Any]) -> str:
        """Build prompt for template-based email composition"""
        
        template_prompts = {
            "meeting_request": f"""
            Compose a professional meeting request email using this context:
            
            RECIPIENT: {context.get('recipient_name', 'Colleague')}
            PURPOSE: {context.get('purpose', 'General discussion')}
            PROPOSED_TIME: {context.get('proposed_time', 'Flexible')}
            DURATION: {context.get('duration', '30 minutes')}
            LOCATION: {context.get('location', 'To be determined')}
            
            Write in markdown format with appropriate greeting, clear purpose, 
            proposed time options, and professional closing.
            """,
            
            "follow_up": f"""
            Compose a professional follow-up email using this context:
            
            PREVIOUS_INTERACTION: {context.get('previous_interaction', 'Previous communication')}
            PURPOSE: {context.get('purpose', 'Follow up')}
            NEXT_STEPS: {context.get('next_steps', 'To be discussed')}
            TIMELINE: {context.get('timeline', 'As soon as possible')}
            
            Write in markdown format with appropriate greeting, reference to 
            previous interaction, clear purpose, and next steps.
            """,
            
            "thank_you": f"""
            Compose a professional thank you email using this context:
            
            RECIPIENT: {context.get('recipient_name', 'Colleague')}
            REASON: {context.get('reason', 'General appreciation')}
            SPECIFIC_ACTION: {context.get('specific_action', 'Their help/support')}
            FUTURE_COLLABORATION: {context.get('future_collaboration', 'Looking forward to working together')}
            
            Write in markdown format with sincere appreciation, specific details, 
            and professional closing.
            """
        }
        
        return template_prompts.get(template_type, f"""
        Compose a professional email using this template type: {template_type}
        
        CONTEXT: {context}
        
        Write in markdown format with appropriate greeting, clear content, 
        and professional closing.
        """)

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
                    attachments=email["attachments"],
                    category=email["category"]
                ))
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
            print(0)
            to_user_ids = []
            for email in email_data.to_users:
                user = await User.find_one(User.email == email)
                if not user:
                    print(f"User with email {email} not found")
                    raise HTTPException(status_code=404, detail=f"User with email {email} not found")
                to_user_ids.append(user.id)
 
            # Find or create thread
            thread = await Thread.find_one({
                "participants": {"$all": [ObjectId(user_id)] + to_user_ids}
            })
            if not thread:
                # Create new thread
                thread = Thread(participants=[ObjectId(user_id)] + to_user_ids)
                thread.lastUpdated = datetime.now(timezone.utc)
                await thread.insert()
            print(3)
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
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error sending email: {str(e)}"
            )

    @staticmethod
    async def send_email_via_smtp(user_id: str, email_data: EmailCreate) -> Dict[str, Any]:
        """Send email via SMTP to actual email addresses"""
        try:
            # Get sender user details
            print('Sending mail using SMTP')
            sender = await User.get(ObjectId(user_id))
            if not sender:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sender not found"
                )
            
            # Get recipient email addresses
            recipient_emails = email_data.to_users
            # Check if SMTP settings are configured
            if not all([settings.SMTP_SERVER, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="SMTP settings not configured. Please configure SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD."
                )
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = sender.email
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = email_data.subject
            
            # Add body
            if email_data.body:
                # Check if body is HTML or plain text
                if '<html>' in email_data.body or '<body>' in email_data.body:
                    msg.attach(MIMEText(email_data.body, 'html'))
                else:
                    msg.attach(MIMEText(email_data.body, 'plain'))
            
            # Add attachments if any
            if email_data.attachments:
                for attachment in email_data.attachments:
                    if hasattr(attachment, 'filename') and hasattr(attachment, 'content'):
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment.filename}'
                        )
                        msg.attach(part)
            
            # Connect to SMTP server and send email
            try:
                if settings.SMTP_USE_TLS:
                    server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT)
                
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                # Store email in database after successful sending
                email_response = await EmailService.send_email(user_id, email_data)
                
                return {
                    "success": True,
                    "message": f"Email sent successfully to {', '.join(recipient_emails)}",
                    "email_id": email_response.id,
                    "recipients": recipient_emails
                }
                
            except smtplib.SMTPAuthenticationError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="SMTP authentication failed. Please check your SMTP credentials."
                )
            except smtplib.SMTPRecipientsRefused as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to send email to some recipients: {e}"
                )
            except smtplib.SMTPServerDisconnected:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="SMTP server disconnected unexpectedly."
                )
            except Exception as e:
                print(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"SMTP error: {str(e)}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error sending email via SMTP: {str(e)}"
            )

    @staticmethod
    async def send_bulk_email_via_smtp(user_id: str, email_data: EmailCreate, recipient_emails: List[str]) -> Dict[str, Any]:
        """Send bulk email via SMTP to multiple email addresses"""
        try:
            # Get sender user details
            sender = await User.get(ObjectId(user_id))
            if not sender:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sender not found"
                )
            
            # Check if SMTP settings are configured
            if not all([settings.SMTP_SERVER, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="SMTP settings not configured. Please configure SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD."
                )
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = sender.email
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = email_data.subject
            
            # Add body
            if email_data.body:
                if '<html>' in email_data.body or '<body>' in email_data.body:
                    msg.attach(MIMEText(email_data.body, 'html'))
                else:
                    msg.attach(MIMEText(email_data.body, 'plain'))
            
            # Add attachments if any
            if email_data.attachments:
                for attachment in email_data.attachments:
                    if hasattr(attachment, 'filename') and hasattr(attachment, 'content'):
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment.filename}'
                        )
                        msg.attach(part)
            
            # Connect to SMTP server and send email
            try:
                if settings.SMTP_USE_TLS:
                    server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT)
                
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                return {
                    "success": True,
                    "message": f"Bulk email sent successfully to {len(recipient_emails)} recipients",
                    "recipients": recipient_emails,
                    "total_sent": len(recipient_emails)
                }
                
            except smtplib.SMTPAuthenticationError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="SMTP authentication failed. Please check your SMTP credentials."
                )
            except smtplib.SMTPRecipientsRefused as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to send email to some recipients: {e}"
                )
            except smtplib.SMTPServerDisconnected:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="SMTP server disconnected unexpectedly."
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"SMTP error: {str(e)}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error sending bulk email via SMTP: {str(e)}"
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