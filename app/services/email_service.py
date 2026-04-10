import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid

from app.config import settings


class EmailService:
    @staticmethod
    def send_welcome_email(to_email: str, temp_password: str) -> bool:
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
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
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
            return True
        except Exception:
            return False
