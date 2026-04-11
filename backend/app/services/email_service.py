"""
Email Service

Sends HTML email notifications via SMTP (e.g. QQ Mail, Gmail, SMTP2Go).
Configured entirely through environment variables – if SMTP_HOST is not set
the service silently no-ops so existing functionality is never disrupted.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """
    SMTP-based email notification service.

    Usage::

        svc = EmailService.from_settings()
        svc.send_task_completed_email(
            to_email="user@example.com",
            task_id="abc123",
            status="completed",
        )
    """

    def __init__(
        self,
        smtp_host: Optional[str],
        smtp_port: int,
        smtp_user: Optional[str],
        smtp_password: Optional[str],
        smtp_from: Optional[str],
    ):
        self._host     = smtp_host
        self._port     = smtp_port
        self._user     = smtp_user
        self._password = smtp_password
        self._from     = smtp_from or smtp_user  # fall back to user address

    @property
    def is_configured(self) -> bool:
        """Return True only if the minimum SMTP settings are present."""
        return bool(self._host and self._user and self._password)

    @classmethod
    def from_settings(cls) -> "EmailService":
        """Instantiate from the application settings singleton."""
        from backend.app.core.config import get_settings
        s = get_settings()
        return cls(
            smtp_host=s.smtp_host,
            smtp_port=s.smtp_port,
            smtp_user=s.smtp_user,
            smtp_password=s.smtp_password,
            smtp_from=s.smtp_from,
        )

    def send_task_completed_email(
        self,
        to_email: str,
        task_id: str,
        status: str,
        title: Optional[str] = None,
    ) -> bool:
        """
        Send a task-completion (or failure) notification email.

        Args:
            to_email:  Recipient email address.
            task_id:   The translation task ID.
            status:    Final task status string, e.g. "completed" / "failed".
            title:     Optional human-friendly task title / paper name.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        if not self.is_configured:
            logger.info(
                "[EmailService] SMTP not configured – skipping email notification. "
                "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in your .env to enable."
            )
            return False

        is_success = status in ("completed", "completed_with_warnings")
        subject = (
            f"✅ 翻译完成 – PaperX" if is_success
            else f"❌ 翻译失败 – PaperX"
        )
        task_label = title or task_id
        status_cn = (
            "已成功完成" if status == "completed"
            else ("已完成（含警告）" if status == "completed_with_warnings"
                  else "处理失败")
        )

        html_body = f"""\
<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8" /></head>
<body style="font-family:system-ui,sans-serif;background:#f5f5f5;margin:0;padding:40px;">
  <div style="max-width:520px;margin:auto;background:#ffffff;border-radius:12px;
              padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.08);">
    <h2 style="margin-top:0;color:{'#16a34a' if is_success else '#dc2626'};">
      {'✅ 翻译完成' if is_success else '❌ 翻译失败'}
    </h2>
    <p style="color:#374151;">您的翻译任务 <strong>{task_label}</strong> {status_cn}。</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
      <tr>
        <td style="padding:8px 0;color:#6b7280;font-size:14px;">任务 ID</td>
        <td style="padding:8px 0;font-family:monospace;font-size:13px;color:#111827;">{task_id}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:#6b7280;font-size:14px;">状态</td>
        <td style="padding:8px 0;font-size:14px;color:{'#16a34a' if is_success else '#dc2626'};">
          {status_cn}
        </td>
      </tr>
    </table>
    <p style="font-size:12px;color:#9ca3af;margin-top:24px;">
      此邮件由 PaperX 系统自动发送，请勿回复。
    </p>
  </div>
</body>
</html>
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = self._from
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            # Extract plain email address for SMTP envelope (display name
            # like "Name <addr>" triggers 501 on some servers).
            _, envelope_from = parseaddr(self._from)
            if not envelope_from:
                envelope_from = self._from  # fallback

            context = ssl.create_default_context()
            if self._port == 465:
                # SSL
                with smtplib.SMTP_SSL(self._host, self._port, context=context) as server:
                    server.login(self._user, self._password)
                    server.sendmail(envelope_from, [to_email], msg.as_string())
            else:
                # STARTTLS (587) or plain (25)
                with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                    server.ehlo()
                    if self._port != 25:
                        server.starttls(context=context)
                        server.ehlo()
                    server.login(self._user, self._password)
                    server.sendmail(envelope_from, [to_email], msg.as_string())

            logger.info(
                f"[EmailService] Notification sent to {to_email} "
                f"(task={task_id}, status={status})"
            )
            return True

        except Exception as e:
            logger.error(
                f"[EmailService] Failed to send notification to {to_email}: {e}",
                exc_info=True,
            )
            return False


# ── Module-level singleton (initialised lazily) ──────────────────────────────

_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Return (or create) the module-level EmailService singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService.from_settings()
    return _email_service
