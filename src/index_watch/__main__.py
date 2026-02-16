"""Entry point for running as python -m index_watch."""

import logging
import sys

from dotenv import load_dotenv

from index_watch.bot import build_application, setup_scheduler
from index_watch.config import Config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    config = Config.from_env()
    if not config.telegram_bot_token:
        logger.error("Bot token not set for current ENV; set BOT_TOKEN or BOT_TOKEN_DEV in .env")
        sys.exit(1)
    app = build_application(config)
    setup_scheduler(app, config)
    logger.info(
        "Starting bot; daily report cron=%s, alert check every %s min",
        config.daily_report_cron,
        config.alert_check_minutes,
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
