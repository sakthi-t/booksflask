import os
import requests
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


class EmailService:
    @staticmethod
    def generate_reset_token(email):
        """Generate a secure password reset token"""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(email, salt='password-reset-salt')
    
    @staticmethod
    def verify_reset_token(token, expiration=3600):
        """Verify password reset token (default: 1 hour expiration)"""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
            return email
        except (SignatureExpired, BadSignature):
            return None
    
    @staticmethod
    def send_password_reset_email(to_email, token):
        """Send password reset email via Brevo API"""
        api_key = os.environ.get('BREVO_API_KEY')
        domain_url = os.environ.get('DOMAIN_URL', 'http://127.0.0.1:5000')
        from_email = os.environ.get('FROM_EMAIL', 'admin@bookscart.com')
        from_name = os.environ.get('FROM_NAME', 'BooksCart Support')
        
        reset_url = f"{domain_url}/auth/reset-password?token={token}"
        
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key
        }
        
        data = {
            "sender": {
                "name": from_name,
                "email": from_email
            },
            "to": [{
                "email": to_email
            }],
            "subject": "Reset Your Password - BooksCart",
            "htmlContent": f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 30px; background-color: #f8f9fa; }}
                    .button {{ display: inline-block; padding: 12px 30px; background-color: #007bff; 
                              color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset Request</h1>
                    </div>
                    <div class="content">
                        <h2>Hello!</h2>
                        <p>You requested a password reset for your BooksCart account.</p>
                        <p>Click the button below to reset your password:</p>
                        <a href="{reset_url}" class="button">Reset My Password</a>
                        <p><strong>This link will expire in 1 hour.</strong></p>
                        <p>If you didn't request this password reset, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 BooksCart. All rights reserved.</p>
                        <p>If you're having trouble clicking the button, copy and paste this URL:<br>
                        <small>{reset_url}</small></p>
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            return response.status_code == 201
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {e}")
            return False
