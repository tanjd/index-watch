"""Format drawdown and alert messages for Telegram."""

from index_watch.drawdown import DrawdownMetrics
from index_watch.fear_greed import FearGreedResult


def format_drawdown_block(name: str, m: DrawdownMetrics) -> str:
    """Format one index's drawdown metrics as a text block."""
    return f"""<b>{name} Drawdown Metrics</b>
Current Drawdown: {m.current_drawdown_pct:.2f}%
Last Closing Price: {m.current_price:,.2f}
All Time High: {m.ath:,.2f}
Lowest Price Since All Time High: {m.lowest_since_ath:,.2f}
Drawdown At Lowest Price Since All Time High: {m.drawdown_at_lowest_pct:.2f}%

Gain From Lowest Price: {m.gain_from_lowest_pct:.2f}%
Gain Required to Reach All Time High From Current Price: {m.gain_to_ath_from_current_pct:.2f}%
Gain Required to Reach All Time High From Lowest Price: {m.gain_to_ath_from_lowest_pct:.2f}%"""


def format_fear_greed(fg: FearGreedResult | None) -> str:
    """Format Fear & Greed line for daily report."""
    if fg is None:
        return "CNN Fear & Greed Index: unavailable"
    return f"CNN Fear & Greed Index: {fg.value:.1f} — {fg.description} (updated {fg.last_update})"


def format_historical_frequency(
    name: str,
    thresholds_pct: tuple[int, ...],
    day_counts: dict[int, int],
    total_days: int,
) -> str:
    """Format how often drawdown exceeded each threshold (for alerts or report)."""
    lines = [f"<b>{name}</b> — historical trading days at or below drawdown:"]
    for t in thresholds_pct:
        count = day_counts.get(t, 0)
        pct = (count / total_days * 100) if total_days else 0
        lines.append(f"  • {t}% drawdown: {count} days ({pct:.1f}% of history)")
    return "\n".join(lines)


def format_daily_report(
    index_blocks: list[tuple[str, str]],  # (name, formatted_block)
    fear_greed_line: str,
    history_blocks: list[str],  # optional historical frequency per index
) -> str:
    """Assemble full daily report message."""
    parts = ["<b>Daily Index Watch</b>\n"]
    for name, block in index_blocks:
        parts.append(block)
        parts.append("")
    parts.append(fear_greed_line)
    if history_blocks:
        parts.append("")
        parts.append("<b>Historical drawdown frequency</b>")
        for block in history_blocks:
            parts.append(block)
    return "\n".join(parts).strip()


def format_drawdown_alert(
    name: str,
    current_drawdown_pct: float,
    threshold_pct: int,
    day_count: int,
    total_days: int,
) -> str:
    """Format alert when drawdown crosses a threshold."""
    pct_of_history = (day_count / total_days * 100) if total_days else 0
    return (
        f"<b>Drawdown alert: {name}</b>\n"
        f"Current drawdown: {current_drawdown_pct:.2f}% (threshold: {threshold_pct}%)\n"
        f"Historically, the index closed at or below {threshold_pct}% drawdown on "
        f"{day_count} trading days ({pct_of_history:.1f}% of the last ~{total_days} days)."
    )
