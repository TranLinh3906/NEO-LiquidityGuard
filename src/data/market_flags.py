"""Join SSI ``market.flag`` events to quotes without guessing session state."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


VN_TZ = timezone(timedelta(hours=7))


def parse_provider_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        try:
            parsed = datetime.strptime(str(value), "%Y/%m/%d %H:%M:%S").replace(tzinfo=VN_TZ)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=VN_TZ)
    return parsed


@dataclass(frozen=True, slots=True)
class MarketFlag:
    board: str
    trading_time: str
    flag: str
    received_at_utc: str | None = None


class MarketFlagJoiner:
    """Keep flags for one connected session and match only same-board earlier flags."""

    def __init__(self) -> None:
        self._flags: dict[str, list[tuple[datetime, MarketFlag]]] = {}
        self.session_uncertain = True

    def clear(self) -> None:
        self._flags.clear()
        self.session_uncertain = True

    def mark_connected(self) -> None:
        self.clear()

    def update(self, board: str, trading_time: str, flag: str, received_at_utc: str | None = None) -> bool:
        parsed = parse_provider_time(trading_time)
        normalized_board = str(board or "").strip().upper()
        normalized_flag = str(flag or "").strip().upper()
        if not normalized_board or not normalized_flag or parsed is None:
            return False
        event = MarketFlag(normalized_board, str(trading_time), normalized_flag, received_at_utc)
        bucket = self._flags.setdefault(normalized_board, [])
        bucket.append((parsed, event))
        bucket.sort(key=lambda item: item[0])
        self.session_uncertain = False
        return True

    def phase_for(self, board: str | None, quote_time: str | None) -> dict[str, Any]:
        normalized_board = str(board or "").strip().upper()
        parsed_quote = parse_provider_time(quote_time)
        if self.session_uncertain or not normalized_board or parsed_quote is None:
            return {"market_phase": None, "market_phase_source": "UNKNOWN", "market_phase_board": normalized_board or None, "market_phase_received_at": None}
        candidates = [
            (when, event)
            for when, event in self._flags.get(normalized_board, [])
            if when.date() == parsed_quote.date() and when <= parsed_quote
        ]
        if not candidates:
            return {"market_phase": None, "market_phase_source": "UNKNOWN", "market_phase_board": normalized_board, "market_phase_received_at": None}
        _, event = candidates[-1]
        return {
            "market_phase": event.flag,
            "market_phase_source": "SSI_MARKET_FLAG",
            "market_phase_board": event.board,
            "market_phase_received_at": event.received_at_utc,
        }
