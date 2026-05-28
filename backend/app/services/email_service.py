"""邮件通知服务

通过 SMTP 发送 HTML 邮件通知（支持 QQ 邮箱、Gmail、SMTP2Go 等）。
完全通过环境变量配置——如果 SMTP_HOST 未设置，服务会静默跳过，不影响现有功能。
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
    """基于 SMTP 的邮件通知服务

    用法::

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
        """初始化邮件服务

        参数:
            smtp_host: SMTP 服务器主机名
            smtp_port: SMTP 端口（465 SSL / 587 STARTTLS）
            smtp_user: SMTP 认证用户名
            smtp_password: SMTP 认证密码
            smtp_from: 发件人地址（未设置时回退到 smtp_user）
        """
        self._host     = smtp_host
        self._port     = smtp_port
        self._user     = smtp_user
        self._password = smtp_password
        self._from     = smtp_from or smtp_user  # 回退到用户地址

    @property
    def is_configured(self) -> bool:
        """仅当最低 SMTP 配置齐全时返回 True"""
        return bool(self._host and self._user and self._password)

    @classmethod
    def from_settings(cls) -> "EmailService":
        """从应用配置单例实例化邮件服务"""
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
        """发送任务完成（或失败）通知邮件

        参数:
            to_email: 收件人邮箱地址
            task_id: 翻译任务 ID
            status: 最终任务状态字符串，如 "completed" / "failed"
            title: 可选的人类可读任务标题/论文名称

        返回:
            邮件发送成功返回 True，否则返回 False
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
            # 提取纯邮件地址用于 SMTP 信封（某些服务器拒绝带显示名的格式，如 "Name <addr>"）
            _, envelope_from = parseaddr(self._from)
            if not envelope_from:
                envelope_from = self._from  # 回退

            context = ssl.create_default_context()
            if self._port == 465:
                # SSL 直连模式
                with smtplib.SMTP_SSL(self._host, self._port, context=context) as server:
                    server.login(self._user, self._password)
                    server.sendmail(envelope_from, [to_email], msg.as_string())
            else:
                # STARTTLS 模式 (587) 或明文模式 (25)
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


# ── 模块级单例（延迟初始化）──────────────────────────────────────────

_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """返回（或创建）模块级 EmailService 单例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService.from_settings()
    return _email_service
