from dataclasses import dataclass
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from data.normalize_quotes import normalise_envelope
from ssi_api.client import SSIReadOnlyClient, jsonable
from ssi_api.config import SSISettings
from ssi_api.live_check import run
from ssi_api.read_only_guard import SSIReadOnlyViolation, assert_ssi_read_only


@dataclass
class SampleMessage:
    symbol: str
    values: list[int]


def test_ssi_settings_and_sdk_defaults(tmp_path, monkeypatch):
    for name in ("SSI_API_URL", "SSI_STREAMING_URL", "SSI_CLIENT_ID", "SSI_API_KEY", "SSI_API_SECRET", "SSI_SYMBOLS"):
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / ".env"
    env.write_text("SSI_CLIENT_ID=client\nSSI_API_KEY=key\nSSI_API_SECRET=secret\nSSI_SYMBOLS=vpb,fpt\n", encoding="utf-8")
    settings = SSISettings.from_env(env)
    assert settings.missing_credentials() == ()
    assert settings.api_url == "https://api.ssi.com.vn"
    assert settings.streaming_url == "wss://stream.ssi.com.vn/ws/v3"
    assert settings.symbols == ("VPB", "FPT")
    assert settings.retry_delay_ms == 2_000
    assert settings.heartbeat_interval_ms == 30_000
    assert Path(settings.ca_bundle).is_file()


def test_ssi_guard_blocks_trading_operations():
    assert_ssi_read_only("data.securities_summary")
    assert_ssi_read_only("stream.quote")
    assert_ssi_read_only("auth.refresh")
    assert_ssi_read_only("data.ohlc")
    with pytest.raises(SSIReadOnlyViolation): assert_ssi_read_only("trading.order.place")


def test_missing_credentials_are_blocked_before_network(tmp_path):
    import ssi_api.live_check as live_check
    from data.raw_writer import RawWriter

    settings = SSISettings(status_path=tmp_path / "status.json")
    report = live_check.run(settings, RawWriter(tmp_path / "raw"), listen_seconds=0)
    assert report["status"] == "CONFIG_REQUIRED"
    assert report["acceptance"]["reason"] == "MISSING_CREDENTIALS"
    assert json.loads((tmp_path / "status.json").read_text())["state"] == "offline"


def test_http_errors_are_reported_as_types_without_message_leak():
    import ssi_api.live_check as live_check

    for status_code in (401, 403, 429):
        error = RuntimeError("secret-token-must-not-appear")
        error.status_code = status_code
        info = live_check._error_info(error)
        assert info == {"error_type": "RuntimeError", "http_status": status_code}
        assert "secret-token" not in json.dumps(info)
    missing = ModuleNotFoundError("No module named 'ssi_sdk'")
    missing.name = "ssi_sdk"
    assert live_check._error_info(missing) == {
        "error_type": "ModuleNotFoundError", "missing_module": "ssi_sdk"
    }


def test_jsonable_converts_sdk_style_dataclass():
    assert jsonable(SampleMessage("SSI", [1, 2])) == {"symbol": "SSI", "values": [1, 2]}


def test_ssi_quote_normalises_to_existing_l3_contract():
    payload = json.loads(open("tests/fixtures/ssi_quote.json", encoding="utf-8").read())
    envelope = {
        "raw_event_id": "ssi-event-1", "provider": "SSI", "source": "SSI_FASTCONNECT", "mode": "LIVE", "transport": "WS",
        "endpoint_or_channel": "quote", "received_at_utc": "2026-11-09T03:00:00.000Z",
        "provider_timestamp_raw": payload["trading_time"], "payload_hash": "hash", "payload": payload,
    }
    quote = normalise_envelope(envelope, price_unit="VND_PER_SHARE", quantity_unit="SHARES", allowed_phases={"LO"})[0]
    assert quote["provider"] == "SSI" and quote["source"] == "SSI_FASTCONNECT" and quote["source_mode"] == "LIVE"
    assert quote["snapshot_completeness"] == "COMPLETE"
    assert quote["bid_price_1"] == "30000" and quote["ask_qty_3"] == 1200


def test_ssi_quote_multiplier_preserves_raw_and_normalises_with_evidence():
    payload = json.loads(open("tests/fixtures/ssi_quote.json", encoding="utf-8").read())
    payload["bid_prices"] = [30, 29.95, 29.9]
    envelope = {
        "raw_event_id": "ssi-event-unit-1", "provider": "SSI", "source": "SSI_FASTCONNECT", "mode": "LIVE", "transport": "WS",
        "endpoint_or_channel": "quote", "received_at_utc": "2026-11-09T03:00:00.000Z",
        "provider_timestamp_raw": payload["trading_time"], "payload_hash": "hash", "payload": payload,
    }
    quote = normalise_envelope(
        envelope, price_multiplier_to_vnd="1000", quantity_multiplier_to_shares="1",
        unit_evidence_ref="ssi-ticket-123", allowed_phases={"LO"},
    )[0]
    assert quote["raw_bid_price_1"] == 30
    assert quote["bid_price_1"] == "30000"
    assert quote["price_unit"] == "VND_PER_SHARE"
    assert quote["quantity_unit"] == "SHARES"
    assert quote["unit_evidence_ref"] == "ssi-ticket-123"


def test_ssi_multiplier_without_evidence_remains_blocked():
    payload = json.loads(open("tests/fixtures/ssi_quote.json", encoding="utf-8").read())
    envelope = {
        "raw_event_id": "ssi-event-unit-2", "provider": "SSI", "source": "SSI_FASTCONNECT", "mode": "LIVE", "transport": "WS",
        "endpoint_or_channel": "quote", "received_at_utc": "2026-11-09T03:00:00.000Z",
        "provider_timestamp_raw": payload["trading_time"], "payload_hash": "hash", "payload": payload,
    }
    quote = normalise_envelope(envelope, price_multiplier_to_vnd="1000")[0]
    assert quote["is_simulatable"] is False
    assert "MISSING_UNIT_EVIDENCE" in quote["quality_flags"]


def test_token_metadata_and_refresh_never_return_secret_values():
    token = SimpleNamespace(expires_at=100, refresh_token_expires_at=200, can_refresh=True)
    client = SSIReadOnlyClient(SSISettings())
    client.auth = SimpleNamespace(token=token, refresh=lambda: token)
    assert client.token_metadata() == {
        "available": True, "expires_at": 100,
        "refresh_expires_at": 200, "can_refresh": True,
    }
    assert client.refresh() == {
        "expires_at": 100, "refresh_expires_at": 200, "can_refresh": True,
    }


def test_ohlc_client_is_read_only_and_maps_timeframe():
    client = SSIReadOnlyClient(SSISettings())
    class MarketData:
        def get_ohlc_all(self, symbol, timeframe, **kwargs):
            return [{"symbol": symbol, "timeframe": timeframe.value, **kwargs}]
    client.data = SimpleNamespace(market_data=MarketData())
    rows = client.ohlc("fpt", "1d", "2021/01/01", "2021/01/02")
    assert rows[0]["symbol"] == "FPT" and rows[0]["timeframe"] == "1d"


def test_live_acceptance_requires_quote_persist_and_readback(tmp_path, monkeypatch):
    import ssi_api.live_check as live_check
    import ssi_sdk
    from data.raw_writer import RawWriter

    class FakeClient:
        def __init__(self, settings): self.auth = object()
        def connect(self): return None
        def token_metadata(self): return {"available": True, "can_refresh": True}
        def securities_info(self, symbol): return {"symbol": symbol}
        def securities_summary(self, symbol): return [{"symbol": symbol}]
        def master_data(self): return [{"symbol": "VPB"}]
        def close(self): return None

    class QuoteMessage:
        def __init__(self):
            self.type = "quote"; self.symbol = "VPB"
            self.trading_time = "2026-11-09T10:00:00+07:00"
            self.bid_prices = [30000, 29950, 29900]; self.bid_volumes = [10, 9, 8]
            self.ask_prices = [30050, 30100, 30150]; self.ask_volumes = [7, 6, 5]

    class MarketFlagMessage:
        def __init__(self):
            self.board = "HOSE"; self.trading_time = "2026-11-09T09:15:00+07:00"; self.flag = "LO"

    class ConnectionEvent:
        def __init__(self, state="connected", reconnect_count=0):
            self.state = state
            self.reconnect_count = reconnect_count

    class FakeStreaming:
        reconnect_count = 0
        on_data = on_market_flag = on_connection = on_heartbeat = None
        last = None
        def __init__(self):
            self.subscribe_calls = 0
            self.subscribe_order = []
            FakeStreaming.last = self
        def connect(self): self.on_connection(ConnectionEvent())
        def ping(self, **kwargs): return None
        def subscribe_symbol_quote(self, symbols, on_response=None):
            self.subscribe_calls += 1
            self.subscribe_order.append("quote")
            on_response({"ok": True})
        def subscribe_market_flag(self, on_response=None):
            self.subscribe_calls += 1
            self.subscribe_order.append("market.flag")
            on_response({"ok": True})
        def list_subscription(self, timeout_ms=5000): return {"data": ["quote.VPB", "quote.FPT"], "trading": []}
        def wait(self, timeout_ms=None):
            self.on_connection(ConnectionEvent("reconnected", 1))
            self.on_market_flag(MarketFlagMessage())
            self.on_data(QuoteMessage())
        def unsubscribe_all(self): return {"data": ["quote.VPB", "quote.FPT"], "trading": []}

    class FakeStream:
        def __init__(self, auth): self.streaming = FakeStreaming()
        def __enter__(self): return self
        def __exit__(self, *args): return None

    monkeypatch.setattr(live_check, "SSIReadOnlyClient", FakeClient)
    monkeypatch.setattr(ssi_sdk, "Stream", FakeStream)
    settings = SSISettings(
        client_id="client", api_key="key", api_secret="secret", symbols=("VPB", "FPT"),
        status_path=tmp_path / "status.json",
    )
    report = run(settings, RawWriter(tmp_path / "raw"), listen_seconds=0.01)
    assert report["acceptance"]["status"] == "PASS"
    assert report["stream"]["quote_count"] == 1
    assert report["stream"]["reconnect_count"] == 0  # fake exposes SDK counter separately
    assert report["stream"]["connection_events"][-1]["state"] == "reconnected"
    assert report["stream"]["subscription_ack"]["quote"] == "RECEIVED"
    assert FakeStreaming.last.subscribe_calls == 4  # quote+flag initially and after reconnect
    assert FakeStreaming.last.subscribe_order == ["market.flag", "quote", "market.flag", "quote"]
    assert report["readback"]["raw_quotes_found"] == 1
    assert report["readback"]["canonical_quotes_parsed"] == 1
    assert report["stream"]["market_flag_count"] == 1
    assert report["stream"]["phase_join_status"] == "VERIFIED"
