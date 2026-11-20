"""Append-only raw-envelope persistence for REST and WebSocket events."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4
try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback keeps append-only mode
    fcntl = None

SENSITIVE_KEYS = frozenset({
    "authorization", "token", "access_token", "accesstoken", "refresh_token",
    "refreshtoken", "password", "secret", "api_key", "apikey", "api_secret",
    "apisecret", "client_secret", "clientsecret", "jwt",
})


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class RawWriter:
    def __init__(self, root: str | Path = "data/raw", schema_version: str = "2.0-draft"):
        self.root, self.schema_version = Path(root), schema_version

    def envelope(self, *, transport: str, endpoint_or_channel: str, payload: Any, provider: str = "SSI", source: str = "SSI_FASTCONNECT", mode: str = "SYNTHETIC_TEST", symbol_hint: str | None = None, provider_timestamp_raw: str | None = None, connection_id: str | None = None, sequence_no: int | None = None, http_status: int | None = None, market_phase: str | None = None, market_phase_source: str | None = None, market_phase_board: str | None = None, market_phase_received_at: str | None = None) -> dict[str, Any]:
        transport = transport.upper()
        if transport not in {"REST", "WS"}:
            raise ValueError("transport must be REST or WS")
        mode = mode.upper()
        if mode not in {"LIVE", "REPLAY", "SYNTHETIC_TEST"}:
            raise ValueError("mode must be LIVE, REPLAY or SYNTHETIC_TEST")
        safe_payload = redact(payload)
        encoded = json.dumps(safe_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        return {
            "schema_version": self.schema_version, "raw_event_id": str(uuid4()),
            "provider": provider, "source": source, "mode": mode,
            "transport": transport, "endpoint_or_channel": endpoint_or_channel,
            "symbol_hint": symbol_hint.upper() if symbol_hint else None, "received_at_utc": utc_now_iso(),
            "provider_timestamp_raw": provider_timestamp_raw, "connection_id": connection_id,
            "sequence_no": sequence_no, "http_status": http_status, "payload": safe_payload,
            "payload_hash": hashlib.sha256(encoded).hexdigest(),
            "market_phase": market_phase, "market_phase_source": market_phase_source,
            "market_phase_board": market_phase_board, "market_phase_received_at": market_phase_received_at,
        }

    def append(self, envelope: dict[str, Any]) -> Path:
        transport = envelope.get("transport")
        if transport not in {"REST", "WS"}:
            raise ValueError("Envelope transport is missing or invalid")
        path = self.root / transport.lower() / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return path

    def write(self, **kwargs: Any) -> dict[str, Any]:
        envelope = self.envelope(**kwargs)
        self.append(envelope)
        return envelope
