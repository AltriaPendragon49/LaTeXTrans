"""Repository layer for local database persistence."""

from backend.app.repositories.auth_repository import AuthRepository
from backend.app.repositories.user_settings_repository import (
    USER_SETTINGS_DEFAULTS,
    UserSettingsRepository,
)
from backend.app.repositories.translation_task_repository import (
    TRANSLATION_TASK_COLUMNS,
    TranslationTaskRepository,
)
from backend.app.repositories.translation_quota_repository import (
    TranslationQuotaRepository,
)
from backend.app.repositories.community_agent_repository import (
    CommunityAgentConversationRepository,
)
from backend.app.repositories.community_paper_repository import (
    CommunityPaperRepository,
    PAPER_COLUMNS,
    PAPER_ASSET_COLUMNS,
)

__all__ = [
    "AuthRepository",
    "UserSettingsRepository",
    "USER_SETTINGS_DEFAULTS",
    "TranslationTaskRepository",
    "TRANSLATION_TASK_COLUMNS",
    "TranslationQuotaRepository",
    "CommunityAgentConversationRepository",
    "CommunityPaperRepository",
    "PAPER_COLUMNS",
    "PAPER_ASSET_COLUMNS",
]
