"""Fetch index prices and compute metrics using yfinance."""

from datetime import datetime, timedelta, timezone

import yfinance as yf

from index_watch.drawdown import (
    DrawdownMetrics,
    compute_ath_and_lowest_since_ath,
    compute_drawdown_metrics,
)


def fetch_index_history(symbol: str, years: int = 20) -> list[float]:
    """Fetch historical daily close prices (oldest first). Returns empty list on failure."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=years * 365)
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start, end=end, auto_adjust=True)
        if hist is None or hist.empty:
            return []
        closes = hist["Close"].dropna().tolist()
        return [float(c) for c in closes]
    except Exception:
        return []


def get_index_metrics(symbol: str, display_name: str, years: int = 20) -> DrawdownMetrics | None:
    """Get drawdown metrics for an index. Returns None if data unavailable."""
    closes = fetch_index_history(symbol, years=years)
    if len(closes) < 2:
        return None
    current_price = closes[-1]
    ath, lowest_since_ath = compute_ath_and_lowest_since_ath(closes)
    return compute_drawdown_metrics(current_price, ath, lowest_since_ath)


def count_trading_days_at_or_below_drawdown(closes: list[float], threshold_pct: float) -> int:
    """Count how many trading days the index closed at or below this drawdown from its then-ATH."""
    if not closes or threshold_pct >= 0:
        return 0
    # threshold_pct is e.g. -5 for "5% drawdown"
    threshold_ratio = 1 + (threshold_pct / 100)
    count = 0
    ath = closes[0]
    for p in closes:
        if p > ath:
            ath = p
        if ath > 0 and p / ath <= threshold_ratio:
            count += 1
    return count


def historical_drawdown_frequency(
    closes: list[float], thresholds_pct: tuple[int, ...]
) -> dict[int, int]:
    """Days at or below each drawdown threshold (e.g. 5, 10, 15, 20)."""
    return {t: count_trading_days_at_or_below_drawdown(closes, -t) for t in thresholds_pct}
