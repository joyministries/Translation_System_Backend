import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from app.config import settings


logger = logging.getLogger(__name__)

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "logo.jpeg")


def _build_html_email(body_content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f4f4f4; font-family: Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f4; padding: 30px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header with Logo -->
                    <tr>
                        <td align="center" style="background-color:#1a5276; padding: 30px 20px;">
                            <img src="cid:logo" alt="Team Impact Christian University" width="120" style="display:block; border-radius: 50%;">
                            <h2 style="color:#ffffff; margin: 15px 0 5px 0; font-size: 18px;">Team Impact Christian University</h2>
                            <p style="color:#aed6f1; margin: 0; font-size: 12px; font-style: italic;">Spirit Filled. Affordable. Practical.</p>
                        </td>
                    </tr>
                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            {body_content}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8f9fa; padding: 20px 30px; border-top: 1px solid #e9ecef;">
                            <p style="color:#6c757d; font-size: 12px; margin: 0; text-align: center;">
                                Team Impact Christian University<br>
                                <a href="https://www.tiuniversity.com" style="color:#1a5276; text-decoration:none;">www.tiuniversity.com</a>
                            </p>
                            <p style="color:#adb5bd; font-size: 11px; margin: 10px 0 0 0; text-align: center;">
                                This is an automated message. Please do not reply directly to this email.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def _attach_logo(msg: MIMEMultipart) -> None:
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as f:
                logo = MIMEImage(f.read(), _subtype="jpeg")
                logo.add_header("Content-ID", "<logo>")
                logo.add_header("Content-Disposition", "inline", filename="logo.jpeg")
                msg.attach(logo)
    except Exception as e:
        logger.warning(f"Could not attach logo: {e}")


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured")
        return False

    msg = MIMEMultipart("related")
    msg["From"] = f"Team Impact Christian University <{settings.SMTP_FROM}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    html_part = MIMEMultipart("alternative")
    html_part.attach(MIMEText(html_body, "html"))
    msg.attach(html_part)

    _attach_logo(msg)

    try:
        port = int(settings.SMTP_PORT) if settings.SMTP_PORT else 465
        logger.info(f"Sending email to {to_email} via {settings.SMTP_HOST}:{port}")
        if port == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, port) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, port) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


class EmailService:
    @staticmethod
    def send_welcome_email(to_email: str, temp_password: str) -> bool:
        body = f"""
            <h3 style="color:#1a5276; margin-top:0;">Welcome to Team Impact Christian University</h3>
            <p style="color:#333; line-height:1.6;">
                Your account has been successfully created. Below are your login credentials:
            </p>
            <table style="background-color:#f8f9fa; border-radius:6px; padding:20px; width:100%; margin: 20px 0;">
                <tr>
                    <td style="padding:10px 20px;">
                        <p style="margin:0; color:#555; font-size:14px;"><strong>Email:</strong></p>
                        <p style="margin:5px 0 15px 0; color:#1a5276; font-size:16px;">{to_email}</p>
                        <p style="margin:0; color:#555; font-size:14px;"><strong>Temporary Password:</strong></p>
                        <p style="margin:5px 0 0 0; color:#1a5276; font-size:16px; font-family:monospace; background:#e8f4fd; padding:8px 12px; border-radius:4px; display:inline-block;">{temp_password}</p>
                    </td>
                </tr>
            </table>
            <p style="color:#333; line-height:1.6;">
                For your security, please log in and change your password immediately upon first access.
            </p>
            <p style="color:#6c757d; font-size:13px; margin-top:25px; padding-top:15px; border-top:1px solid #e9ecef;">
                If you did not expect this email, please contact your administrator.
            </p>
        """
        html = _build_html_email(body)
        return _send_email(to_email, "Welcome — Your Account Credentials", html)

    @staticmethod
    def send_password_reset_email(to_email: str, reset_link: str) -> bool:
        body = f"""
            <h3 style="color:#1a5276; margin-top:0;">Password Reset Request</h3>
            <p style="color:#333; line-height:1.6;">
                We received a request to reset your password. Click the button below to create a new password:
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                <tr>
                    <td align="center">
                        <a href="{reset_link}" style="background-color:#1a5276; color:#ffffff; padding:14px 32px; text-decoration:none; border-radius:6px; font-size:16px; font-weight:bold; display:inline-block;">
                            Reset Password
                        </a>
                    </td>
                </tr>
            </table>
            <p style="color:#6c757d; font-size:13px; line-height:1.6;">
                If the button doesn't work, copy and paste this link into your browser:<br>
                <a href="{reset_link}" style="color:#1a5276; word-break:break-all;">{reset_link}</a>
            </p>
            <p style="color:#333; line-height:1.6;">
                This link will expire in <strong>1 hour</strong>. If you did not request a password reset, 
                please ignore this email — your account remains secure.
            </p>
        """
        html = _build_html_email(body)
        return _send_email(to_email, "Password Reset — Team Impact Christian University", html)
