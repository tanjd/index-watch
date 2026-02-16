"""Telegram bot handlers and scheduled jobs."""

import asyncio
import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from index_watch.alerts import AlertState
from index_watch.config import Config
from index_watch.fear_greed import fetch_fear_greed
from index_watch.formatting import (
    format_daily_report,
    format_drawdown_alert,
    format_drawdown_block,
    format_fear_greed,
    format_historical_frequency,
)
from index_watch.index_data import (
    fetch_index_history,
    get_index_metrics,
    historical_drawdown_frequency,
)

logger = logging.getLogger(__name__)

alert_state = AlertState()


def _build_daily_report(config: Config) -> str:
    """Build the full daily report text (sync, for use from async)."""
    index_blocks: list[tuple[str, str]] = []
    history_blocks: list[str] = []

    for symbol, name in config.index_symbols.items():
        metrics = get_index_metrics(symbol, name, years=config.history_years)
        if metrics:
            index_blocks.append((name, format_drawdown_block(name, metrics)))
            closes = fetch_index_history(symbol, years=config.history_years)
            if closes:
                freq = historical_drawdown_frequency(closes, config.drawdown_thresholds_pct)
                history_blocks.append(
                    format_historical_frequency(
                        name, config.drawdown_thresholds_pct, freq, len(closes)
                    )
                )

    fear_greed = fetch_fear_greed()
    fear_greed_line = format_fear_greed(fear_greed)
    return format_daily_report(index_blocks, fear_greed_line, history_blocks)


async def send_daily_report(app: Application[Any, Any, Any, Any, Any, Any], config: Config) -> None:
    """Scheduled job: send daily report to all chat_ids."""
    if not config.chat_ids:
        logger.warning("No TELEGRAM_CHAT_IDS configured; skipping daily report")
        return
    report = await asyncio.to_thread(_build_daily_report, config)
    for chat_id in config.chat_ids:
        try:
            await app.bot.send_message(chat_id=chat_id, text=report, parse_mode="HTML")
        except Exception as e:
            logger.exception("Failed to send daily report to %s: %s", chat_id, e)


def _check_drawdown_alerts(config: Config) -> list[tuple[str, str]]:
    """Check all indices for threshold breaches; return list of (chat_id, message) to send."""
    results: list[tuple[str, str]] = []
    for symbol, name in config.index_symbols.items():
        metrics = get_index_metrics(symbol, name, years=config.history_years)
        if not metrics:
            continue
        closes = fetch_index_history(symbol, years=config.history_years)
        total_days = len(closes)
        alert_state.on_drawdown_improved(
            symbol, metrics.current_drawdown_pct, config.drawdown_thresholds_pct
        )
        for threshold in config.drawdown_thresholds_pct:
            if not alert_state.should_alert(symbol, threshold, metrics.current_drawdown_pct):
                continue
            freq = historical_drawdown_frequency(closes, (threshold,))
            day_count = freq.get(threshold, 0)
            msg = format_drawdown_alert(
                name, metrics.current_drawdown_pct, threshold, day_count, total_days
            )
            for chat_id in config.chat_ids:
                results.append((chat_id, msg))
            alert_state.mark_sent(symbol, threshold)
    return results


async def check_and_send_alerts(
    app: Application[Any, Any, Any, Any, Any, Any], config: Config
) -> None:
    """Scheduled job: check drawdown thresholds and send alerts."""
    if not config.chat_ids:
        return
    to_send = await asyncio.to_thread(_check_drawdown_alerts, config)
    for chat_id, text in to_send:
        try:
            await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.exception("Failed to send alert to %s: %s", chat_id, e)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start."""
    if not update.message:
        return
    await update.message.reply_text(
        "Index Watch — crash-buy helper.\n\n"
        "Commands:\n"
        "• /daily — get today's drawdown report\n"
        "• /alerts — show configured drawdown thresholds\n"
        "Set TELEGRAM_CHAT_IDS to receive daily reports and drawdown alerts."
    )


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /daily — manual daily report."""
    if not update.message:
        return
    config = context.bot_data.get("config")
    if not config:
        await update.message.reply_text("Config not loaded.")
        return
    report = await asyncio.to_thread(_build_daily_report, config)
    await update.message.reply_text(report, parse_mode="HTML")


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alerts — show configured thresholds."""
    if not update.message:
        return
    config = context.bot_data.get("config")
    if not config:
        await update.message.reply_text("Config not loaded.")
        return
    th = ", ".join(str(t) + "%" for t in config.drawdown_thresholds_pct)
    parts = [f"Drawdown alert thresholds: {th}"]
    parts.append(f"Indices: {', '.join(config.index_symbols.values())}")
    parts.append(f"Alert check interval: every {config.alert_check_minutes} minutes")
    await update.message.reply_text("\n".join(parts))


def setup_scheduler(
    app: Application[Any, Any, Any, Any, Any, Any], config: Config
) -> AsyncIOScheduler:
    """Add scheduled jobs for daily report and drawdown checks."""
    scheduler = AsyncIOScheduler()

    cron_kw = _cron_from_cronstr(config.daily_report_cron) or {"hour": 22, "minute": 0}
    scheduler.add_job(
        send_daily_report,
        "cron",
        args=[app, config],
        **cron_kw,
    )

    scheduler.add_job(
        check_and_send_alerts,
        "interval",
        args=[app, config],
        minutes=config.alert_check_minutes,
    )

    app.bot_data["scheduler"] = scheduler
    return scheduler


async def _on_application_ready(application: Application[Any, Any, Any, Any, Any, Any]) -> None:
    """Run when the app is ready (event loop is up): start the scheduler."""
    scheduler = application.bot_data.get("scheduler")
    if scheduler is not None:
        scheduler.start()
        logger.info("Scheduler started")


def _cron_from_cronstr(cron: str) -> dict[str, Any]:
    """Parse cron 'minute hour day month weekday' into apscheduler kwargs (non-wildcard only)."""
    parts = cron.split()
    if len(parts) != 5:
        return {}
    minute, hour, day, month, weekday = parts
    out: dict[str, Any] = {}
    if minute != "*":
        out["minute"] = minute
    if hour != "*":
        out["hour"] = hour
    if day != "*":
        out["day"] = day
    if month != "*":
        out["month"] = month
    if weekday != "*":
        out["day_of_week"] = weekday
    return out


def build_application(config: Config) -> Application[Any, Any, Any, Any, Any, Any]:
    """Create and configure the Telegram application."""
    app = (
        Application.builder()
        .token(config.telegram_bot_token)
        .post_init(_on_application_ready)
        .build()
    )
    app.bot_data["config"] = config
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    return app
