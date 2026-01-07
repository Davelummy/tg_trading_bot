from bot.middleware import _is_admin
from services.config_service import BotSettings


def test_admin_guard_allows_admin():
    settings = BotSettings(ADMIN_TELEGRAM_IDS="123,456")
    assert _is_admin(123, settings)


def test_admin_guard_blocks_non_admin():
    settings = BotSettings(ADMIN_TELEGRAM_IDS="123,456")
    assert not _is_admin(999, settings)
