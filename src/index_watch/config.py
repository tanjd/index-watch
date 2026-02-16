"""Configuration from environment."""

import os
from dataclasses import dataclass, field

DEFAULT_INDEX_SYMBOLS = {"^GSPC": "S&P 500", "^NDX": "NASDAQ-100"}
DEFAULT_DRAWDOWN_THRESHOLDS = (5, 10, 15, 20)
DEFAULT_DAILY_REPORT_CRON = "0 22 * * 1-5"  # 22:00 UTC Mon–Fri (after US close)
DEFAULT_ALERT_CHECK_MINUTES = 30


@dataclass
class Config:
    """Bot and data configuration."""

    telegram_bot_token: str = ""
    chat_ids: list[str] = field(default_factory=list)
    index_symbols: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_INDEX_SYMBOLS))
    drawdown_thresholds_pct: tuple[int, ...] = DEFAULT_DRAWDOWN_THRESHOLDS
    daily_report_cron: str = DEFAULT_DAILY_REPORT_CRON
    alert_check_minutes: int = DEFAULT_ALERT_CHECK_MINUTES
    history_years: int = 20

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables."""
        env = os.getenv("ENV", "").strip().lower()
        token_dev = (os.getenv("BOT_TOKEN_DEV") or "").strip()
        token_prd = (os.getenv("BOT_TOKEN") or "").strip()
        token = token_dev if env == "dev" else token_prd

        raw_chat_ids = os.getenv("TELEGRAM_CHAT_IDS", "").strip()
        chat_ids = [c.strip() for c in raw_chat_ids.split(",") if c.strip()]

        raw_thresholds = os.getenv("DRAWDOWN_THRESHOLDS_PCT", "").strip()
        if raw_thresholds:
            thresholds = tuple(int(x) for x in raw_thresholds.replace("%", "").split())
        else:
            thresholds = DEFAULT_DRAWDOWN_THRESHOLDS

        return cls(
            telegram_bot_token=token,
            chat_ids=chat_ids,
            drawdown_thresholds_pct=thresholds,
            daily_report_cron=os.getenv("DAILY_REPORT_CRON", DEFAULT_DAILY_REPORT_CRON).strip()
            or DEFAULT_DAILY_REPORT_CRON,
            alert_check_minutes=int(
                os.getenv("ALERT_CHECK_MINUTES", str(DEFAULT_ALERT_CHECK_MINUTES))
            ),
            history_years=int(os.getenv("HISTORY_YEARS", "20")),
        )
