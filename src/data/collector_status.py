"""Durable, UI-readable collector health state."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(slots=True)
class CollectorStatus:
    provider: str = "SSI"
    source: str = "SSI_FASTCONNECT"
    state: str = "offline"
    last_message_at_utc: str | None = None
    last_error: str | None = None
    message_count: int = 0
    quote_count: int = 0
    last_quote_at_utc: str | None = None
    connection_id: str | None = None
    subscriptions: list[str] = field(default_factory=list)
    reconnect_count: int = 0
    heartbeat_count: int = 0
    last_heartbeat_at_utc: str | None = None
    updated_at_utc: str = field(default_factory=_now)

    def connected(self, connection_id: str, subscriptions: list[str], reconnect_count: int = 0) -> None:
        self.state, self.connection_id, self.subscriptions, self.last_error = "online", connection_id, subscriptions, None
        self.reconnect_count = reconnect_count
        self.updated_at_utc = _now()

    def message_received(self) -> None:
        self.message_count += 1
        self.last_message_at_utc = self.updated_at_utc = _now()

    def quote_received(self) -> None:
        self.message_received()
        self.quote_count += 1
        self.last_quote_at_utc = self.updated_at_utc

    def failed(self, error: Exception | str) -> None:
        self.state, self.last_error, self.updated_at_utc = "offline", f"{type(error).__name__}: {error}" if isinstance(error, Exception) else str(error), _now()

    def heartbeat(self) -> None:
        self.heartbeat_count += 1
        self.last_heartbeat_at_utc = self.updated_at_utc = _now()

    def stopped(self) -> None:
        self.state, self.last_error, self.updated_at_utc = "offline", None, _now()

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)

    @classmethod
    def load(cls, path: str | Path) -> "CollectorStatus":
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)
