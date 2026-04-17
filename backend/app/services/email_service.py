"""
Email service — async SMTP via aiosmtplib.

Sends:
  - Email verification links
  - Password reset links

Configure via .env:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, FRONTEND_URL
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Template helpers ────────────────────────────────────────────────────────

def _html_base(title: str, body_html: str) -> str:
    """Minimal responsive email HTML wrapper."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f0f; color: #e0e0e0; margin: 0; padding: 20px; }}
    .container {{ max-width: 520px; margin: 40px auto; background: #1a1a1a;
                  border-radius: 12px; padding: 40px; border: 1px solid #2a2a2a; }}
    h1 {{ font-size: 22px; color: #ffffff; margin-top: 0; }}
    p  {{ line-height: 1.6; color: #b0b0b0; }}
    .btn {{ display: inline-block; padding: 14px 28px; background: #7c3aed;
            color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600;
            margin: 24px 0; }}
    .note {{ font-size: 13px; color: #666; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="container">
    {body_html}
    <p class="note">If you did not request this, you can safely ignore this email.</p>
  </div>
</body>
</html>"""


def _verification_html(full_name: str, verify_url: str) -> str:
    name = full_name or "there"
    return _html_base(
        "Verify your VoiceRAG email",
        f"""
        <h1>Welcome to VoiceRAG!</h1>
        <p>Hi {name},</p>
        <p>Thanks for signing up. Please confirm your email address to activate your account.</p>
        <a href="{verify_url}" class="btn">Verify Email</a>
        <p>Or copy this link into your browser:<br>
           <small>{verify_url}</small></p>
        <p class="note">This link expires in 24 hours.</p>
        """,
    )


def _password_reset_html(full_name: str, reset_url: str) -> str:
    name = full_name or "there"
    return _html_base(
        "Reset your VoiceRAG password",
        f"""
        <h1>Password Reset Request</h1>
        <p>Hi {name},</p>
        <p>We received a request to reset your VoiceRAG password. Click the button below.</p>
        <a href="{reset_url}" class="btn">Reset Password</a>
        <p>Or copy this link:<br><small>{reset_url}</small></p>
        <p class="note">This link expires in 1 hour. If you did not request a reset, ignore this email.</p>
        """,
    )


# ── Core send function ──────────────────────────────────────────────────────

async def _send_email(to: str, subject: str, html: str) -> None:
    """Send an HTML email via aiosmtplib. Logs a warning if SMTP is not configured."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            f"[Email] SMTP not configured — would send '{subject}' to {to}.\n"
            "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in .env to enable emails."
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.SMTP_FROM
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info(f"[Email] Sent '{subject}' to {to}")
    except Exception as e:
        logger.error(f"[Email] Failed to send to {to}: {e}")
        # Don't raise — email failure should not block registration/login


# ── Public API ──────────────────────────────────────────────────────────────

async def send_verification_email(to: str, full_name: str, token: str) -> None:
    url  = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = _verification_html(full_name, url)
    await _send_email(to, "Verify your VoiceRAG email address", html)


async def send_password_reset_email(to: str, full_name: str, token: str) -> None:
    url  = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = _password_reset_html(full_name, url)
    await _send_email(to, "Reset your VoiceRAG password", html)
