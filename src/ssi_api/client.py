"""Thin read-only façade around the official SSI SDK."""
from __future__ import annotations
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .config import SSISettings
from .read_only_guard import assert_ssi_read_only


def jsonable(value: Any) -> Any:
    if is_dataclass(value): return {key: jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum): return value.value
    if isinstance(value, dict): return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)): return [jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    if hasattr(value, "to_dict"): return jsonable(value.to_dict())
    if hasattr(value, "__dict__"): return {key: jsonable(item) for key, item in vars(value).items() if not key.startswith("_")}
    return str(value)


class SSIReadOnlyClient:
    def __init__(self, settings: SSISettings):
        self.settings = settings
        self.auth = None
        self.data = None

    def connect(self) -> None:
        assert_ssi_read_only("auth.authenticate")
        from ssi_sdk import Auth, Data
        self.auth = Auth(self.settings.sdk_config())
        # Initial Market Data login requires no OTP. Subsequent calls can use
        # ensure_authenticated()/refresh() with the in-memory refresh token.
        self.auth.authenticate()
        self.auth.ensure_authenticated()
        self.data = Data(self.auth)

    def refresh(self) -> dict[str, Any]:
        assert_ssi_read_only("auth.refresh")
        token = self.auth.refresh()
        return {
            "expires_at": token.expires_at,
            "refresh_expires_at": token.refresh_token_expires_at,
            "can_refresh": token.can_refresh,
        }

    def token_metadata(self) -> dict[str, Any]:
        token = self.auth.token if self.auth is not None else None
        if token is None:
            return {"available": False}
        return {
            "available": True,
            "expires_at": token.expires_at,
            "refresh_expires_at": token.refresh_token_expires_at,
            "can_refresh": token.can_refresh,
        }

    def securities_info(self, symbol: str) -> Any:
        assert_ssi_read_only("data.securities_info")
        return self.data.market_data.get_securities_info(symbol.upper())

    def securities_summary(self, symbol: str) -> Any:
        assert_ssi_read_only("data.securities_summary")
        return self.data.market_data.get_securities_summary(symbol.upper())

    def master_data(self) -> Any:
        assert_ssi_read_only("data.master_data")
        return self.data.market_data.get_master_data()

    def securities_by_board(self, board: str) -> Any:
        assert_ssi_read_only("data.securities_by_board")
        from ssi_sdk.enums import Board
        return self.data.market_data.get_securities_info_by_board(Board(board.upper()))

    def market_summary(self, symbol: str, from_date: str, to_date: str) -> Any:
        """Daily trading history, using the SDK's automatic paging and rate cap."""
        assert_ssi_read_only("data.market_summary")
        return self.data.market_data.get_securities_summary_historical(symbol.upper(),from_date,to_date)

    def ohlc(self, symbol: str, timeframe: str = "1d", from_date: str | None = None,
             to_date: str | None = None, *, size: int = 1000, ascending: bool = True) -> Any:
        """Fetch read-only OHLCV candles through SSI's paginated SDK service."""
        assert_ssi_read_only("data.ohlc")
        from ssi_sdk.enums.timeframe import Timeframe
        try:
            tf = Timeframe(str(timeframe))
        except ValueError as exc:
            raise ValueError("timeframe must be one of 1m, 3m, 5m, 15m, 1h or 1d") from exc
        return self.data.market_data.get_ohlc_all(
            symbol.upper(), tf, from_date=from_date, to_date=to_date,
            size=size, ascending=ascending,
        )

    def close(self) -> None:
        if self.auth is not None: self.auth.close()
