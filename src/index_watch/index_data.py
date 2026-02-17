"""Fetch index prices and compute metrics using yfinance."""

import logging
from datetime import datetime, timedelta, timezone

import yfinance as yf

from index_watch.cache import get_cache
from index_watch.drawdown import (
    DrawdownMetrics,
    compute_ath_and_lowest_since_ath,
    compute_drawdown_metrics,
)

logger = logging.getLogger(__name__)

# Cache TTL: 30 minutes for index data (matches alert check interval)
CACHE_TTL_SECONDS = 30 * 60


def fetch_index_history(symbol: str, years: int = 20) -> tuple[list[float], datetime]:
    """
    Fetch historical daily close prices (oldest first) with caching.

    Returns:
        tuple of (closes, fetched_at) - closes is empty list on failure,
        fetched_at is when data was retrieved (UTC)
    """
    cache = get_cache()
    cache_key = f"index_history:{symbol}:{years}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached:
        closes, fetched_at = cached
        logger.info(
            "Using cached data for %s (%d days, cached %d seconds ago)",
            symbol,
            len(closes),
            int((datetime.now(timezone.utc) - fetched_at).total_seconds()),
        )
        return closes, fetched_at

    # Fetch fresh data
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=years * 365)
    fetched_at = datetime.now(timezone.utc)

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start, end=end, auto_adjust=True)
        if hist is None or hist.empty:
            logger.warning(
                "No data returned for %s (start=%s, end=%s)",
                symbol,
                start.date(),
                end.date(),
            )
            return [], fetched_at

        closes = hist["Close"].dropna().tolist()
        result = [float(c) for c in closes]
        logger.info("Fetched %d days of history for %s", len(result), symbol)

        # Cache the result
        cache.set(cache_key, result, CACHE_TTL_SECONDS)
        return result, fetched_at

    except Exception as e:
        logger.error("Failed to fetch data for %s: %s", symbol, e, exc_info=True)
        return [], fetched_at


def get_index_metrics(
    symbol: str, display_name: str, years: int = 20
) -> tuple[DrawdownMetrics, datetime] | None:
    """
    Get drawdown metrics for an index with data timestamp.

    Returns:
        tuple of (metrics, fetched_at) or None if data unavailable
    """
    closes, fetched_at = fetch_index_history(symbol, years=years)
    if len(closes) < 2:
        return None
    current_price = closes[-1]
    ath, lowest_since_ath = compute_ath_and_lowest_since_ath(closes)
    metrics = compute_drawdown_metrics(current_price, ath, lowest_since_ath)
    return metrics, fetched_at


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
