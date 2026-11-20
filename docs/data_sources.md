# Data Sources and Limitations

The sole source is SSI FastConnect Market Data REST and Quote Streaming. Raw captures retain `provider=SSI`, `source=SSI_FASTCONNECT`, mode, endpoint/channel, receive timestamp, raw-event ID and payload hash. Included fixtures are `SYNTHETIC_TEST`; they are not SSI LIVE captures and cannot establish market-data coverage.

All technical receive times are UTC. Presentation time is converted to `Asia/Ho_Chi_Minh` only after a trustworthy provider timestamp rule is verified. Since 19/11/2026, SSI support evidence confirms Quote prices are VND, quantities are shares and the current message contains the latest complete book. W3 uses multiplier `1/1`; empty `["0","0"]` levels remain non-executable.

Historical OHLC is explicitly out of scope for L3 reconstruction. It can support price-history analysis, but it cannot prove intraday spread, three-level depth or OBI. Those claims require stored SSI QuoteMessage history.
