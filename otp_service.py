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
        # Redis configuration for storing OTPs temporarily
        self.redis_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )

        # Email configuration
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@arstudios.com')

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
        """Store OTP in Redis with expiration"""
        hashed_otp = self.hash_otp(otp)
        key = f"otp:{purpose}:{email}"

        # Store OTP data
        otp_data = {
            'hashed_otp': hashed_otp,
            'created_at': datetime.utcnow().isoformat(),
            'attempts': 0,
            'purpose': purpose
        }

        # Set expiration to 2 minutes (120 seconds) to give some buffer
        self.redis_client.setex(key, 120, json.dumps(otp_data))

        return True

    def verify_otp(self, email, otp, purpose='login'):
        """Verify OTP and return success status"""
        key = f"otp:{purpose}:{email}"
        stored_data = self.redis_client.get(key)

        if not stored_data:
            return False, "OTP has expired or doesn't exist"

        try:
            otp_data = json.loads(stored_data)
        except json.JSONDecodeError:
            return False, "Invalid OTP data"

        # Check attempts
        if otp_data.get('attempts', 0) >= self.max_attempts:
            self.redis_client.delete(key)
            return False, "Too many failed attempts. Please request a new OTP."

        # Verify OTP
        hashed_input = self.hash_otp(otp)
        if hashed_input != otp_data['hashed_otp']:
            # Increment attempts
            otp_data['attempts'] += 1
            self.redis_client.setex(key, 120, json.dumps(otp_data))
            return False, "Invalid OTP"

        # OTP is valid, delete it to prevent reuse
        self.redis_client.delete(key)
        return True, "OTP verified successfully"

    def send_otp_email(self, email, otp, purpose='login'):
        """Send OTP via email"""
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

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.from_email, email, text)
            server.quit()

            return True, "OTP sent successfully"

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
