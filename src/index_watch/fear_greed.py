"""CNN Fear & Greed Index fetcher."""

from dataclasses import dataclass


@dataclass
class FearGreedResult:
    """Fear and Greed index result."""

    value: float
    description: str
    last_update: str  # human-readable or ISO


def fetch_fear_greed() -> FearGreedResult | None:
    """Fetch current CNN Fear & Greed Index. Returns None on failure."""
    try:
        import fear_and_greed

        fg = fear_and_greed.get()
        return FearGreedResult(
            value=fg.value,
            description=fg.description or "Unknown",
            last_update=(
                fg.last_update.isoformat()
                if getattr(fg.last_update, "isoformat", None)
                else str(fg.last_update)
            ),
        )
    except Exception:
        return None
