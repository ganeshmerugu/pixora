"""Email service — SMTP for verification, password reset, notifications.

Set PIXORA_SMTP_HOST + PIXORA_SMTP_USER + PIXORA_SMTP_PASSWORD to enable.
Falls back to logging emails when SMTP not configured.
"""
from __future__ import annotations
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> bool:
    from pixora.config.settings import settings

    if not settings.smtp_host:
        logger.info("email: [DRY RUN] To=%s Subject=%s", to, subject)
        return True

    try:
        import aiosmtplib
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
        )
        logger.info("email: sent to %s — %s", to, subject)
        return True
    except Exception as exc:
        logger.error("email: failed to send to %s: %s", to, exc)
        return False


async def send_verification_email(to: str, token: str, base_url: str = "https://pixora.onrender.com") -> bool:
    html = f"""
    <h2>Verify your Pixora account</h2>
    <p>Click the link below to verify your email:</p>
    <a href="{base_url}/verify?token={token}" style="
        display: inline-block; padding: 12px 24px;
        background: #6366f1; color: white; text-decoration: none;
        border-radius: 8px; font-weight: bold;">
        Verify Email
    </a>
    <p style="color: #666; margin-top: 16px;">
        This link expires in 24 hours. If you didn't create a Pixora account, ignore this email.
    </p>
    """
    return await send_email(to, "Verify your Pixora account", html)


async def send_password_reset_email(to: str, token: str, base_url: str = "https://pixora.onrender.com") -> bool:
    html = f"""
    <h2>Reset your password</h2>
    <p>Click the link below to reset your password:</p>
    <a href="{base_url}/reset-password?token={token}" style="
        display: inline-block; padding: 12px 24px;
        background: #6366f1; color: white; text-decoration: none;
        border-radius: 8px; font-weight: bold;">
        Reset Password
    </a>
    <p style="color: #666; margin-top: 16px;">
        This link expires in 1 hour. If you didn't request this, ignore this email.
    </p>
    """
    return await send_email(to, "Reset your Pixora password", html)


async def send_welcome_email(to: str, name: str) -> bool:
    html = f"""
    <h2>Welcome to Pixora, {name}!</h2>
    <p>Your account is ready. You have <strong>50 free documents</strong> to get started.</p>
    <p>Upload any document — invoice, medical record, ID card, contract — and watch Pixora extract structured data in seconds.</p>
    <a href="https://pixora.onrender.com/parse" style="
        display: inline-block; padding: 12px 24px;
        background: #6366f1; color: white; text-decoration: none;
        border-radius: 8px; font-weight: bold;">
        Parse Your First Document
    </a>
    """
    return await send_email(to, f"Welcome to Pixora, {name}!", html)
