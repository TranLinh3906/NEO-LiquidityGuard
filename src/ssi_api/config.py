"""SSI FastConnect configuration loaded exclusively from environment variables."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import os
from dotenv import load_dotenv
from .symbol_groups import VN30_SYMBOLS, resolve_symbols


def _as_bool(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"1", "true", "yes", "on"})


def _as_decimal(value: str | None) -> Decimal | None:
    """Parse an explicitly supplied unit multiplier; blank means unverified."""
    if value is None or not value.strip():
        return None
    try:
        number = Decimal(value.strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("SSI unit multipliers must be positive decimals") from exc
    if number <= 0:
        raise ValueError("SSI unit multipliers must be positive decimals")
    return number


@dataclass(frozen=True, slots=True)
class SSISettings:
    api_url: str = "https://api.ssi.com.vn"
    streaming_url: str = "wss://stream.ssi.com.vn/ws/v3"
    client_id: str = ""
    api_key: str = ""
    api_secret: str = ""
    symbols: tuple[str, ...] = VN30_SYMBOLS
    collection_scope: str = "VN30"
    timeout_ms: int = 10_000
    max_retries: int = 3
    retry_delay_ms: int = 2_000
    max_rps: int = 5
    heartbeat_interval_ms: int = 30_000
    ca_bundle: str = ""
    status_path: Path = Path("data/runtime/collector_status.json")
    data_mode: str = "SYNTHETIC_TEST"
    live_confirmed: bool = False
    quote_price_multiplier_to_vnd: Decimal | None = None
    quote_quantity_multiplier_to_shares: Decimal | None = None
    units_evidence_ref: str | None = None
    complete_book_verified: bool = False

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> "SSISettings":
        load_dotenv(env_file, override=False)
        scope = os.getenv("SSI_COLLECTION_SCOPE", "VN30").strip().upper()
        configured = os.getenv("SSI_SYMBOLS", "").split(",")
        raw_root = os.getenv("SSI_UNIVERSE_RAW_ROOT", "data/raw/rest")
        symbols = resolve_symbols(scope, configured, raw_root=raw_root)
        configured_ca = os.getenv("SSI_CA_BUNDLE", "").strip()
        if not configured_ca:
            import certifi
            configured_ca = certifi.where()
        return cls(
            api_url=os.getenv("SSI_API_URL", "https://api.ssi.com.vn").rstrip("/"),
            streaming_url=os.getenv("SSI_STREAMING_URL", "wss://stream.ssi.com.vn/ws/v3"),
            client_id=os.getenv("SSI_CLIENT_ID", ""), api_key=os.getenv("SSI_API_KEY", ""),
            api_secret=os.getenv("SSI_API_SECRET", ""), symbols=symbols,
            collection_scope=scope,
            timeout_ms=int(float(os.getenv("SSI_REQUEST_TIMEOUT", "10")) * 1000),
            max_retries=int(os.getenv("SSI_MAX_RETRIES", "3")),
            retry_delay_ms=int(float(os.getenv("SSI_RETRY_DELAY", "2")) * 1000),
            max_rps=int(os.getenv("SSI_MAX_RPS", "5")),
            heartbeat_interval_ms=int(float(os.getenv("SSI_HEARTBEAT_INTERVAL", "30")) * 1000),
            ca_bundle=configured_ca,
            status_path=Path(os.getenv("SSI_COLLECTOR_STATUS_PATH", "data/runtime/collector_status.json")),
            data_mode=os.getenv("SSI_DATA_MODE", "SYNTHETIC_TEST").upper(),
            live_confirmed=_as_bool(os.getenv("SSI_LIVE_CONFIRMED")),
            quote_price_multiplier_to_vnd=_as_decimal(os.getenv("SSI_QUOTE_PRICE_MULTIPLIER_TO_VND")),
            quote_quantity_multiplier_to_shares=_as_decimal(os.getenv("SSI_QUOTE_QUANTITY_MULTIPLIER_TO_SHARES")),
            units_evidence_ref=os.getenv("SSI_UNITS_EVIDENCE_REF", "").strip() or None,
            complete_book_verified=_as_bool(os.getenv("SSI_COMPLETE_BOOK_VERIFIED")),
        )

    def missing_credentials(self) -> tuple[str, ...]:
        fields = {"SSI_CLIENT_ID": self.client_id, "SSI_API_KEY": self.api_key, "SSI_API_SECRET": self.api_secret}
        return tuple(name for name, value in fields.items() if not value or value.startswith("YOUR_"))

    def unit_policy(self) -> dict[str, object]:
        """Return only explicitly evidenced policy; never infer SSI quote units."""
        return {
            "quote_price_multiplier_to_vnd": self.quote_price_multiplier_to_vnd,
            "quote_quantity_multiplier_to_shares": self.quote_quantity_multiplier_to_shares,
            "evidence_ref": self.units_evidence_ref,
            "complete_book_verified": self.complete_book_verified,
        }

    def sdk_config(self):
        from ssi_sdk import Config
        if self.ca_bundle:
            os.environ.setdefault("WEBSOCKET_CLIENT_CA_BUNDLE", self.ca_bundle)
        return Config(
            client_id=self.client_id, api_key=self.api_key, api_secret=self.api_secret,
            api_url=self.api_url, streaming_url=self.streaming_url, timeout_ms=self.timeout_ms,
            max_retries=self.max_retries, retry_delay_ms=self.retry_delay_ms,
            rate_limit_per_second=self.max_rps,
            auto_reconnect=True, log_level="WARNING",
        )
