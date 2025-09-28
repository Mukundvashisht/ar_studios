import secrets
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
from flask import current_app
import redis
import json


class OTPService:
    def __init__(self):
        # Try to use Redis if available, otherwise use in-memory storage
        self.use_redis = True
        self.redis_client = None
        self.memory_store = {}
        
        try:
            self.redis_client = redis.Redis(
                host=os.environ.get('REDIS_HOST', 'localhost'),
                port=int(os.environ.get('REDIS_PORT', 6379)),
                db=0,
                decode_responses=True,
                socket_connect_timeout=2  # Shorter timeout for faster fallback
            )
            # Test the connection
            self.redis_client.ping()
        except (redis.ConnectionError, redis.TimeoutError):
            self.use_redis = False
            print('Warning: Redis not available, using in-memory OTP storage (not suitable for production)')
            self.redis_client = None

        # Email configuration with better defaults and validation
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', self.smtp_username or 'noreply@example.com')
        
        # Check if email is configured
        self.email_enabled = bool(self.smtp_username and self.smtp_password)
        if not self.email_enabled:
            print('Warning: Email sending is disabled. Set SMTP_USERNAME and SMTP_PASSWORD environment variables to enable email notifications.')

        # OTP configuration
        self.otp_length = 6
        self.otp_expiry_minutes = 1  # 60 seconds
        self.max_attempts = 3

    def generate_otp(self):
        """Generate a secure 6-digit OTP"""
        return str(secrets.randbelow(900000) + 100000)

    def hash_otp(self, otp):
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()

    def store_otp(self, email, otp, purpose='login'):
        """Store OTP in Redis or in-memory with expiration"""
        hashed_otp = self.hash_otp(otp)
        key = f"otp:{purpose}:{email}"

        # Store OTP data
        otp_data = {
            'hashed_otp': hashed_otp,
            'created_at': datetime.utcnow().isoformat(),
            'attempts': 0,
            'purpose': purpose,
            'expires_at': (datetime.utcnow() + timedelta(minutes=2)).isoformat()
        }

        if self.use_redis and self.redis_client:
            try:
                # Set expiration to 2 minutes (120 seconds)
                self.redis_client.setex(key, 120, json.dumps(otp_data))
                return True
            except redis.RedisError as e:
                print(f"Redis error: {e}")
                # Fall through to in-memory storage
                self.use_redis = False
        
        # Fallback to in-memory storage
        self.memory_store[key] = otp_data
        return True

    def _cleanup_expired_otps(self):
        """Remove expired OTPs from memory store"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in self.memory_store.items()
            if datetime.fromisoformat(data['expires_at']) < now
        ]
        for key in expired_keys:
            self.memory_store.pop(key, None)

    def verify_otp(self, email, otp, purpose='login'):
        """Verify OTP and return success status"""
        key = f"otp:{purpose}:{email}"
        
        # Clean up expired OTPs first
        self._cleanup_expired_otps()
        
        # Try Redis first if available
        if self.use_redis and self.redis_client:
            try:
                stored_data = self.redis_client.get(key)
                if stored_data:
                    try:
                        otp_data = json.loads(stored_data)
                        # Check attempts
                        if otp_data.get('attempts', 0) >= self.max_attempts:
                            self.redis_client.delete(key)
                            return False, "Too many failed attempts. Please request a new OTP."

                        # Verify OTP
                        hashed_input = self.hash_otp(otp)
                        if hashed_input == otp_data['hashed_otp']:
                            # OTP is valid, delete it to prevent reuse
                            self.redis_client.delete(key)
                            return True, "OTP verified successfully"
                        else:
                            # Increment attempts
                            otp_data['attempts'] = otp_data.get('attempts', 0) + 1
                            self.redis_client.setex(key, 120, json.dumps(otp_data))
                            return False, "Invalid OTP"
                    except (json.JSONDecodeError, KeyError):
                        pass
            except redis.RedisError:
                # Fall through to in-memory check
                pass
        
        # Check in-memory storage
        if key in self.memory_store:
            otp_data = self.memory_store[key]
            # Check if OTP is expired
            if datetime.fromisoformat(otp_data['expires_at']) < datetime.utcnow():
                self.memory_store.pop(key, None)
                return False, "OTP has expired"
                
            # Check attempts
            if otp_data.get('attempts', 0) >= self.max_attempts:
                self.memory_store.pop(key, None)
                return False, "Too many failed attempts. Please request a new OTP."

            # Verify OTP
            hashed_input = self.hash_otp(otp)
            if hashed_input == otp_data['hashed_otp']:
                # OTP is valid, delete it to prevent reuse
                self.memory_store.pop(key, None)
                return True, "OTP verified successfully"
            else:
                # Increment attempts
                otp_data['attempts'] = otp_data.get('attempts', 0) + 1
                return False, "Invalid OTP"
        
        return False, "OTP has expired or doesn't exist"

    def send_otp_email(self, email, otp, purpose='login'):
        """Send OTP via email"""
        if not self.email_enabled:
            return False, "Email sending is not configured. Please contact support."
            
        if not all([self.smtp_username, self.smtp_password, self.smtp_server]):
            return False, "Email configuration is incomplete. Please check your SMTP settings."
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = f"Your {purpose.title()} Verification Code - AR Studios"

            # Email body
            if purpose == 'login':
                body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h2 style="color: #6366f1; margin: 0;">AR Studios</h2>
                            <p style="color: #666; margin: 5px 0;">Project Management System</p>
                        </div>
                        
                        <div style="background: #f8fafc; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
                            <h3 style="color: #1e293b; margin: 0 0 15px;">Your Login Verification Code</h3>
                            <div style="background: white; padding: 20px; border-radius: 8px; display: inline-block; border: 2px solid #6366f1;">
                                <span style="font-size: 32px; font-weight: bold; color: #6366f1; letter-spacing: 4px;">{otp}</span>
                            </div>
                            <p style="color: #64748b; margin: 15px 0 0; font-size: 14px;">This code will expire in 60 seconds</p>
                        </div>
                        
                        <div style="color: #64748b; font-size: 14px;">
                            <p>If you didn't request this code, please ignore this email.</p>
                            <p>For security reasons, this code can only be used once.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
            else:  # signup
                body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h2 style="color: #6366f1; margin: 0;">AR Studios</h2>
                            <p style="color: #666; margin: 5px 0;">Project Management System</p>
                        </div>
                        
                        <div style="background: #f8fafc; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
                            <h3 style="color: #1e293b; margin: 0 0 15px;">Welcome! Verify Your Email</h3>
                            <p style="color: #64748b; margin: 0 0 20px;">Please use the code below to complete your registration:</p>
                            <div style="background: white; padding: 20px; border-radius: 8px; display: inline-block; border: 2px solid #6366f1;">
                                <span style="font-size: 32px; font-weight: bold; color: #6366f1; letter-spacing: 4px;">{otp}</span>
                            </div>
                            <p style="color: #64748b; margin: 15px 0 0; font-size: 14px;">This code will expire in 60 seconds</p>
                        </div>
                        
                        <div style="color: #64748b; font-size: 14px;">
                            <p>Thank you for joining AR Studios!</p>
                            <p>If you didn't create an account, please ignore this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """

            msg.attach(MIMEText(body, 'html'))

            # Connect to SMTP server and send email
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                    server.ehlo()
                    if self.smtp_server == 'smtp.gmail.com':
                        server.starttls()
                        server.ehlo()
                    
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    
                    server.send_message(msg)
                
                return True, "Email sent successfully"
            except smtplib.SMTPAuthenticationError:
                return False, "Failed to authenticate with the email server. Please check your SMTP credentials."
            except smtplib.SMTPException as e:
                return False, f"Failed to send email: {str(e)}"
            except Exception as e:
                return False, f"An error occurred while sending email: {str(e)}"

        except Exception as e:
            current_app.logger.error(f"Failed to send OTP email: {str(e)}")
            return False, f"Failed to send email: {str(e)}"

    def send_otp(self, email, purpose='login'):
        """Generate, store, and send OTP"""
        try:
            # Generate OTP
            otp = self.generate_otp()

            # Store OTP
            if not self.store_otp(email, otp, purpose):
                return False, "Failed to store OTP"

            # Send email
            success, message = self.send_otp_email(email, otp, purpose)
            if not success:
                return False, message

            return True, "OTP sent successfully"

        except Exception as e:
            current_app.logger.error(f"OTP service error: {str(e)}")
            return False, f"OTP service error: {str(e)}"

    def cleanup_expired_otps(self):
        """Clean up expired OTPs (Redis handles this automatically with TTL)"""
        # Redis automatically handles expiration with TTL
        pass

    def get_otp_status(self, email, purpose='login'):
        """Check if there's a pending OTP for the email"""
        key = f"otp:{purpose}:{email}"
        return self.redis_client.exists(key)


# Create a global instance
otp_service = OTPService()
