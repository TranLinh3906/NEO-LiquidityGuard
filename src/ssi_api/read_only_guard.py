"""Allow only SSI Market Data operations; Trading services are out of scope."""


class SSIReadOnlyViolation(PermissionError):
    pass


ALLOWED_OPERATIONS = frozenset({
    "auth.authenticate", "auth.refresh", "data.securities_info", "data.securities_summary",
    "data.master_data", "stream.quote", "stream.market_flag",
    "data.ohlc",
    "data.market_summary", "data.securities_by_board",
})


def assert_ssi_read_only(operation: str) -> None:
    if operation not in ALLOWED_OPERATIONS:
        raise SSIReadOnlyViolation(f"Blocked non-market-data SSI operation: {operation}")
