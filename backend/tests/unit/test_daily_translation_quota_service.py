import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.core.config import get_settings
from backend.app.services.translation_quota_service import (
    DailyQuotaExceededError,
    TranslationQuotaService,
)


def _create_quota_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            create table users (
              id text primary key,
              external_provider text not null,
              external_user_id text not null,
              email text null,
              display_name text null,
              token_version integer not null default 1,
              status text not null default 'active',
              created_at text not null,
              updated_at text not null
            );

            create table user_daily_quotas (
              user_id text not null,
              quota_type text not null,
              quota_date text not null,
              limit_count integer not null,
              used_count integer not null default 0,
              created_at text not null,
              updated_at text not null,
              primary key (user_id, quota_type, quota_date)
            );

            create table niutrans_balance_snapshots (
              user_id text primary key,
              unused_num_integral integer null,
              status text not null,
              source text not null,
              fetched_at text null,
              updated_at text not null
            );
            """
        )
        connection.execute(
            """
            insert into users (id, external_provider, external_user_id, email, display_name, created_at, updated_at)
            values ('usr_quota_1', 'niutrans', '179017', null, 'Alice', '2026-05-06T00:00:00', '2026-05-06T00:00:00')
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_daily_quota_reserve_reject_release_and_reset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_path = tmp_path / "quota.db"
    _create_quota_schema(database_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    monkeypatch.setattr(settings, "daily_latex_translation_quota_limit", 3)
    monkeypatch.setattr(settings, "daily_latex_translation_quota_timezone", "Asia/Shanghai")

    service = TranslationQuotaService(
        now_provider=lambda: datetime(2026, 5, 6, 15, 30, tzinfo=timezone.utc)
    )

    first = service.reserve_latex_translation(user_id="usr_quota_1", requested_count=2)
    assert first.used == 2
    assert first.remaining == 1
    assert first.quota_date == "2026-05-06"
    assert first.reset_timezone == "Asia/Shanghai"

    with pytest.raises(DailyQuotaExceededError) as exc_info:
        service.reserve_latex_translation(user_id="usr_quota_1", requested_count=2)

    assert exc_info.value.snapshot.used == 2
    assert exc_info.value.snapshot.remaining == 1
    assert exc_info.value.requested_count == 2

    released = service.release_latex_translation(user_id="usr_quota_1", count=1)
    assert released.used == 1
    assert released.remaining == 2

    next_day = TranslationQuotaService(
        now_provider=lambda: datetime(2026, 5, 6, 16, 1, tzinfo=timezone.utc)
    )
    reset_snapshot = next_day.get_latex_translation_snapshot("usr_quota_1")
    assert reset_snapshot.quota_date == "2026-05-07"
    assert reset_snapshot.used == 0
    assert reset_snapshot.remaining == 3


def test_niutrans_balance_snapshot_persists_only_safe_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "quota.db"
    _create_quota_schema(database_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")

    service = TranslationQuotaService()
    service.store_pdf_direct_snapshot(
        user_id="usr_quota_1",
        unused_num_integral=60,
        status="available",
        fetched_at=datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
    )

    snapshot = service.get_quota_snapshot("usr_quota_1")

    assert snapshot["pdf_direct"] == {
        "unused_integral": 60,
        "source": "niutrans",
        "status": "available",
        "fetched_at": "2026-05-06T12:00:00+00:00",
    }
    assert "token" not in str(snapshot).lower()
    assert "apikey" not in str(snapshot).lower()
    assert "password" not in str(snapshot).lower()


def _fixed_utc_now() -> datetime:
    return datetime(2026, 5, 6, 15, 30, tzinfo=timezone.utc)


def test_admin_reserve_skips_db_and_returns_bypass_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Admin reserve_latex_translation does not touch DB and returns bypassed=True."""
    db_path = tmp_path / "admin_reserve.db"
    _create_quota_schema(db_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "daily_latex_translation_quota_limit", 3)
    monkeypatch.setattr(settings, "daily_latex_translation_quota_timezone", "Asia/Shanghai")

    service = TranslationQuotaService(now_provider=_fixed_utc_now)

    snapshot = service.reserve_latex_translation(
        user_id="usr_quota_1", requested_count=1, roles=["admin"]
    )
    assert snapshot.bypassed is True
    assert snapshot.limit == 0
    assert snapshot.used == 0
    assert snapshot.remaining == 0
    assert snapshot.reset_timezone == "Asia/Shanghai"

    # Verify DB was NOT touched - the user's quota should still be at default
    db_snapshot = service.get_latex_translation_snapshot("usr_quota_1")
    assert db_snapshot.used == 0
    assert db_snapshot.remaining == 3
    assert db_snapshot.bypassed is False


def test_admin_release_skips_db_and_returns_bypass_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Admin release_latex_translation does not touch DB."""
    db_path = tmp_path / "admin_release.db"
    _create_quota_schema(db_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "daily_latex_translation_quota_limit", 3)
    monkeypatch.setattr(settings, "daily_latex_translation_quota_timezone", "Asia/Shanghai")

    service = TranslationQuotaService(now_provider=_fixed_utc_now)

    # First reserve as non-admin to use some quota
    service.reserve_latex_translation(user_id="usr_quota_1", requested_count=2, roles=["user"])
    db_snapshot = service.get_latex_translation_snapshot("usr_quota_1")
    assert db_snapshot.used == 2

    # Release as admin should not affect the DB
    snapshot = service.release_latex_translation(user_id="usr_quota_1", count=1, roles=["admin"])
    assert snapshot.bypassed is True

    # DB should still show used=2 (admin release was a no-op)
    db_snapshot2 = service.get_latex_translation_snapshot("usr_quota_1")
    assert db_snapshot2.used == 2


def test_admin_snapshot_bypasses_db_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Admin get_latex_translation_snapshot skips DB query entirely."""
    db_path = tmp_path / "admin_snapshot.db"
    _create_quota_schema(db_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "daily_latex_translation_quota_limit", 3)
    monkeypatch.setattr(settings, "daily_latex_translation_quota_timezone", "Asia/Shanghai")

    service = TranslationQuotaService(now_provider=_fixed_utc_now)

    # Non-admin snapshot reads DB - returns default values for unknown user
    normal = service.get_latex_translation_snapshot("nonexistent_user", roles=["user"])
    assert normal.bypassed is False

    # Admin snapshot skips DB - even for nonexistent user with no prior DB entries
    admin = service.get_latex_translation_snapshot("nonexistent_user", roles=["admin"])
    assert admin.bypassed is True
    assert admin.limit == 0
    assert admin.remaining == 0


def test_is_admin_correctly_detects_role() -> None:
    """_is_admin returns True only for roles containing 'admin' (case-insensitive)."""
    assert TranslationQuotaService._is_admin(["admin"]) is True
    assert TranslationQuotaService._is_admin(["user", "admin"]) is True
    assert TranslationQuotaService._is_admin(["ADMIN"]) is True
    assert TranslationQuotaService._is_admin(["Admin"]) is True
    assert TranslationQuotaService._is_admin(["user"]) is False
    assert TranslationQuotaService._is_admin([]) is False
    assert TranslationQuotaService._is_admin(None) is False
    assert TranslationQuotaService._is_admin(["moderator"]) is False


def test_admin_reserve_never_raises_quota_exceeded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Admin reserve always succeeds even when non-admin quota is exhausted."""
    db_path = tmp_path / "admin_never_blocked.db"
    _create_quota_schema(db_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "daily_latex_translation_quota_limit", 3)
    monkeypatch.setattr(settings, "daily_latex_translation_quota_timezone", "Asia/Shanghai")

    service = TranslationQuotaService(now_provider=_fixed_utc_now)

    # Exhaust non-admin quota first
    service.reserve_latex_translation(user_id="usr_quota_1", requested_count=3, roles=["user"])

    # Verify non-admin is blocked
    try:
        service.reserve_latex_translation(user_id="usr_quota_1", requested_count=1, roles=["user"])
        pytest.fail("Should have raised DailyQuotaExceededError")
    except DailyQuotaExceededError:
        pass

    # Admin with same user_id bypasses the exhausted quota
    snapshot = service.reserve_latex_translation(
        user_id="usr_quota_1", requested_count=99, roles=["admin"]
    )
    assert snapshot.bypassed is True


def test_get_quota_snapshot_for_admin_includes_bypassed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_quota_snapshot shows bypassed=True in latex_translation for admin."""
    db_path = tmp_path / "admin_full_snapshot.db"
    _create_quota_schema(db_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "daily_latex_translation_quota_limit", 3)
    monkeypatch.setattr(settings, "daily_latex_translation_quota_timezone", "Asia/Shanghai")

    service = TranslationQuotaService(now_provider=_fixed_utc_now)

    admin_snap = service.get_quota_snapshot("any_user", roles=["admin"])
    assert admin_snap["latex_translation"]["bypassed"] is True

    non_admin_snap = service.get_quota_snapshot("any_user", roles=["user"])
    assert non_admin_snap["latex_translation"]["bypassed"] is False
