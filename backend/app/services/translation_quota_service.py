from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.repositories.translation_quota_repository import TranslationQuotaRepository

LATEX_TRANSLATION_QUOTA_TYPE = "latex_translation"
PDF_DIRECT_SOURCE = "niutrans"


@dataclass(frozen=True)
class LatexQuotaSnapshot:
    limit: int
    used: int
    remaining: int
    quota_date: str
    reset_timezone: str
    bypassed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "quota_date": self.quota_date,
            "reset_timezone": self.reset_timezone,
            "bypassed": self.bypassed,
        }

    @staticmethod
    def admin_bypass(timezone_name: str) -> "LatexQuotaSnapshot":
        return LatexQuotaSnapshot(
            limit=0,
            used=0,
            remaining=0,
            quota_date="",
            reset_timezone=timezone_name,
            bypassed=True,
        )


@dataclass(frozen=True)
class DailyQuotaExceededError(Exception):
    snapshot: LatexQuotaSnapshot
    requested_count: int


class TranslationQuotaService:
    def __init__(
        self,
        *,
        repository: Optional[TranslationQuotaRepository] = None,
        now_provider: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._settings = get_settings()
        self._repository = repository or TranslationQuotaRepository()
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def get_latex_translation_snapshot(
        self, user_id: str, roles: Optional[list[str]] = None,
    ) -> LatexQuotaSnapshot:
        if self._is_admin(roles):
            return LatexQuotaSnapshot.admin_bypass(self._timezone_name())
        quota_date = self._current_quota_date()
        row = self._repository.ensure_daily_quota(
            user_id=user_id,
            quota_type=LATEX_TRANSLATION_QUOTA_TYPE,
            quota_date=quota_date,
            limit_count=self._daily_limit(),
        )
        return self._snapshot_from_row(row)

    def reserve_latex_translation(
        self,
        *,
        user_id: str,
        requested_count: int,
        roles: Optional[list[str]] = None,
    ) -> LatexQuotaSnapshot:
        if self._is_admin(roles):
            return LatexQuotaSnapshot.admin_bypass(self._timezone_name())
        normalized_count = self._normalize_count(requested_count)
        accepted, row = self._repository.reserve_daily_quota(
            user_id=user_id,
            quota_type=LATEX_TRANSLATION_QUOTA_TYPE,
            quota_date=self._current_quota_date(),
            requested_count=normalized_count,
            limit_count=self._daily_limit(),
        )
        snapshot = self._snapshot_from_row(row)
        if not accepted:
            raise DailyQuotaExceededError(
                snapshot=snapshot,
                requested_count=normalized_count,
            )
        return snapshot

    def release_latex_translation(
        self,
        *,
        user_id: str,
        count: int,
        roles: Optional[list[str]] = None,
    ) -> LatexQuotaSnapshot:
        if self._is_admin(roles):
            return LatexQuotaSnapshot.admin_bypass(self._timezone_name())
        normalized_count = self._normalize_count(count)
        row = self._repository.release_daily_quota(
            user_id=user_id,
            quota_type=LATEX_TRANSLATION_QUOTA_TYPE,
            quota_date=self._current_quota_date(),
            count=normalized_count,
            limit_count=self._daily_limit(),
        )
        return self._snapshot_from_row(row)

    def store_pdf_direct_snapshot(
        self,
        *,
        user_id: str,
        unused_num_integral: Optional[int],
        status: str,
        fetched_at: Optional[datetime],
    ) -> None:
        self._repository.upsert_pdf_direct_snapshot(
            user_id=user_id,
            unused_num_integral=unused_num_integral,
            status=self._normalize_pdf_status(status),
            source=PDF_DIRECT_SOURCE,
            fetched_at=fetched_at,
        )

    def get_quota_snapshot(self, user_id: str, roles: Optional[list[str]] = None) -> dict[str, Any]:
        return {
            "latex_translation": self.get_latex_translation_snapshot(user_id, roles=roles).to_dict(),
            "pdf_direct": self._pdf_direct_snapshot_to_dict(
                self._repository.get_pdf_direct_snapshot_for_user(user_id)
            ),
        }

    def quota_exceeded_payload(self, error: DailyQuotaExceededError) -> dict[str, Any]:
        snapshot = error.snapshot
        return {
            "code": "DAILY_LATEX_QUOTA_EXCEEDED",
            "message": "Daily LaTeX translation quota exceeded.",
            "requested_count": error.requested_count,
            "limit": snapshot.limit,
            "used": snapshot.used,
            "remaining": snapshot.remaining,
            "quota_date": snapshot.quota_date,
            "reset_timezone": snapshot.reset_timezone,
        }

    def _snapshot_from_row(self, row: dict[str, Any]) -> LatexQuotaSnapshot:
        limit = max(int(row.get("limit_count") or 0), 0)
        used = max(int(row.get("used_count") or 0), 0)
        return LatexQuotaSnapshot(
            limit=limit,
            used=used,
            remaining=max(limit - used, 0),
            quota_date=str(row.get("quota_date")),
            reset_timezone=self._timezone_name(),
        )

    def _pdf_direct_snapshot_to_dict(self, row: Optional[dict[str, Any]]) -> dict[str, Any]:
        if row is None:
            return {
                "unused_integral": None,
                "source": PDF_DIRECT_SOURCE,
                "status": "unavailable",
                "fetched_at": None,
            }

        fetched_at = row.get("fetched_at")
        return {
            "unused_integral": row.get("unused_num_integral"),
            "source": str(row.get("source") or PDF_DIRECT_SOURCE),
            "status": self._normalize_pdf_status(str(row.get("status") or "unavailable")),
            "fetched_at": _serialize_datetime(fetched_at),
        }

    def _current_quota_date(self) -> str:
        now = self._now_provider()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(self._quota_timezone()).date().isoformat()

    def _daily_limit(self) -> int:
        return max(int(getattr(self._settings, "daily_latex_translation_quota_limit", 3) or 0), 0)

    def _timezone_name(self) -> str:
        return str(getattr(self._settings, "daily_latex_translation_quota_timezone", "Asia/Shanghai") or "Asia/Shanghai")

    def _quota_timezone(self) -> timezone:
        name = self._timezone_name()
        try:
            return ZoneInfo(name)
        except Exception:
            return timezone(timedelta(hours=8), name="Asia/Shanghai")

    @staticmethod
    def _normalize_count(value: int) -> int:
        count = int(value or 0)
        if count <= 0:
            raise ValueError("requested quota count must be positive")
        return count

    @staticmethod
    def _is_admin(roles: Optional[list[str]]) -> bool:
        if not roles:
            return False
        return "admin" in {str(r).strip().lower() for r in roles}

    @staticmethod
    def _normalize_pdf_status(value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"available", "stale", "unavailable"}:
            return normalized
        return "unavailable"


def _serialize_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
