import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid

from app.config import settings


logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_welcome_email(to_email: str, temp_password: str) -> bool:
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured")
            return False

        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = "Welcome - Your Account Credentials"

        body = f"""Hello,

Your account has been created. Here are your login credentials:

Email: {to_email}
Temporary Password: {temp_password}

Please login and change your password immediately.

Best regards,
Curriculum Management System"""

        msg.attach(MIMEText(body, "plain"))

        try:
            logger.info(
                f"Sending email to {to_email} via {settings.SMTP_HOST}:{settings.SMTP_PORT}"
            )
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                logger.info(f"Logging in as {settings.SMTP_USER}")
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
