# SSI FastConnect V3 — Read-only Runbook

## Scope

This integration uses only SSI Market Data. It never initializes the Trading client, never requests OTP, never loads a private key and never calls place/amend/cancel operations.

Production endpoints:

- REST: `https://api.ssi.com.vn`
- Token: `POST /api/v3/auth/token`
- Market WebSocket: `wss://stream.ssi.com.vn/ws/v3`

## Credentials

Create a Market Data API key in the SSI Developer Portal and put the following values only in the ignored `.env` file:

```dotenv
SSI_CLIENT_ID=...
SSI_API_KEY=...
SSI_API_SECRET=...
SSI_COLLECTION_SCOPE=VN30
SSI_SYMBOLS=
```

Market Data authentication does not require OTP. Do not add an account number, OTP, private key or Trading scope to this project.

## Install and verify

```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
PYTHONPATH=src python -m ssi_api.live_check --listen-seconds 60
```

## Thu OHLCV lịch sử và phân tích thanh khoản

SSI `/api/v3/data/ohlc` trả về `open`, `high`, `low`, `close`, `volume` và
`value`. Dữ liệu daily có thể dùng cho lịch sử dài hạn; dữ liệu 1 phút dùng để
phân tích nội ngày trong cửa sổ intraday mà SSI cấp. Các bar này được lưu ở
`data/processed/ohlc_history.jsonl`, tách khỏi raw quote L3.

```bash
# 5 năm daily cho watchlist đang cấu hình trong SSI_SYMBOLS
PYTHONPATH=src python -m ssi_api.ohlc_collect --timeframe 1d --years 5

# 1 phút: hệ thống tự giới hạn range mặc định theo cửa sổ intraday của SSI
PYTHONPATH=src python -m ssi_api.ohlc_collect --timeframe 1m --years 5

# Chọn 10–50 mã cho cấp B
PYTHONPATH=src python -m ssi_api.ohlc_collect \
  --symbols FPT,VPB,SSI,HPG,VNM,VCB,MWG,TCB,MBB,VIC --timeframe 1d --years 5
```

Không bật toàn bộ danh mục cho LIVE/REST theo mặc định. Cấp A cho phép chọn
toàn bộ mã HOSE/HNX/UPCoM trong catalog; cấp B dùng watchlist 10–50 mã; cấp C
chỉ mở sau khi kiểm chứng quyền SSI, rate limit, thời gian xử lý và dung lượng
lưu trữ.

On success, REST and quote frames are stored under `data/raw/rest/` and `data/raw/ws/` with `provider=SSI`, `source=SSI_FASTCONNECT` and `mode=LIVE`. The evidence report is `outputs/qa/ssi_live_access_check.json`.

The command exits unsuccessfully unless at least one real VPB/FPT `QuoteMessage` is persisted and read back as a canonical quote. Keep `SSI_LIVE_CONFIRMED=false` until `outputs/qa/ssi_live_access_check.json` contains `acceptance.status=PASS`. WebSocket control/heartbeat frames, successful authentication and subscription acknowledgements do not satisfy acceptance.

The collector subscribes to `market.flag` **before** quote channels on both the
initial connection and reconnect. Each flag is saved as its own
raw `market.flag` event. A quote receives a phase only when a flag for the same
board has been received and its provider timestamp is earlier than or equal to
the quote timestamp. A reconnect clears the join state; until a new flag is
received, quotes are explicitly `UNKNOWN` and cannot be used for LIVE
simulation.

Run the acceptance capture during an active HOSE session. The default scope is
the 30-member VN30 basket (HOSE review July 2026), not only `VPB,FPT`.
Available scopes are:

- `VN30`: bounded default; uses the built-in reviewed basket when
  `SSI_SYMBOLS` is blank.
- `WATCHLIST`: uses the explicit comma-separated `SSI_SYMBOLS`; a blank list
  safely falls back to VN30.
- `ALL`: resolves all SSI-classified stocks from locally saved
  `securitiesByBoard` metadata. Use only after verifying SSI subscription
  permissions and workstation capacity.

An explicit `SSI_SYMBOLS` list overrides `WATCHLIST` or `VN30`; it is ignored
by `ALL`. A normal successful report must show:

```text
authentication.status=PASS
stream.quote_count>=1
readback.raw_quotes_found>=1
readback.canonical_quotes_parsed>=1
acceptance.status=PASS
```

## Thu đủ 5 phiên LIVE

Một phiên chỉ được tính khi có quote `mode=LIVE` với ngày provider thật. Ba
ngày hiện có là 16/11, 18/11 và 19/11, nên còn thiếu 2 ngày giao dịch.
Không thể lấp bằng replay hoặc synthetic.

Trong mỗi ngày cần chạy đủ hai cửa sổ, dùng cùng `data/raw` để append lịch sử:

```bash
# Start around 08:55, cover 09:00–11:30 (the early connection helps receive market.flag).
# The wrapper selects the correct virtualenv; the duration is calculated to 11:30 VN.
scripts/capture_ssi_session.sh --window morning \
  --report outputs/qa/ssi_capture_morning_YYYYMMDD.json

# Start around 12:55, cover 13:00–14:45
scripts/capture_ssi_session.sh --window afternoon \
  --report outputs/qa/ssi_capture_afternoon_YYYYMMDD.json
```

Có thể chạy một batch bổ sung đồng thời mà không sửa `.env`. Luôn dùng status
file riêng; `RawWriter` khóa từng lần append để hai tiến trình không trộn dòng:

```bash
scripts/capture_ssi_session.sh --window morning \
  --symbols AAA,ACB,... \
  --status-path data/runtime/collector_status_extra.json \
  --report outputs/qa/ssi_capture_morning_extra.json
```

Với đúng danh sách 230 mã của capture 19/11, khởi động lúc khoảng 08:55 trên
hai ngày giao dịch tiếp theo:

```bash
scripts/capture_next_full_session_230.sh
```

Script giữ kết nối qua cả phiên sáng, nghỉ trưa và phiên chiều đến 14:45; dữ
liệu vẫn append vào raw store. Sau mỗi ngày chạy:

```bash
PYTHONPATH=src python -m data.pipeline data/raw/ws/*.jsonl
scripts/refresh_qa_reports.sh
```

Chỉ khi `session_days_observed >= 5` và từng cửa sổ có dữ liệu gần biên mở/
đóng phiên, báo cáo mới có thể chuyển khỏi `OBSERVED_ONLY`. Việc này vẫn không
tự mở W4 nếu quote không ghép được `market.flag` cùng sàn/thời điểm. Đơn vị
giá VND, khối lượng cổ phiếu và complete-book semantics đã được SSI support
xác nhận ngày 19/11/2026; xem `docs/ssi_quote_schema_confirmation.md`.

## W3/W4 handoff

SSI `QuoteMessage` arrays are mapped as follows:

- `bid_prices[0:3]` → `bid_price_1..3`
- `bid_volumes[0:3]` → `bid_qty_1..3`
- `ask_prices[0:3]` → `ask_price_1..3`
- `ask_volumes[0:3]` → `ask_qty_1..3`

Provider time comes from `trading_time`. A quote remains ineligible for W4 until a verified market phase and concrete price/quantity units are attached.

## Unit verification gate

SSI quote frames do not contain a self-authenticating price or quantity unit.
The current project has provider confirmation dated 19/11/2026 and therefore
uses the following verified policy:

```dotenv
SSI_QUOTE_PRICE_MULTIPLIER_TO_VND=1
SSI_QUOTE_QUANTITY_MULTIPLIER_TO_SHARES=1
SSI_UNITS_EVIDENCE_REF=SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19
SSI_COMPLETE_BOOK_VERIFIED=true
```

After evidence is obtained, set the exact multiplier (including `1` when that
is the verified value) and a ticket/document reference. The normalizer keeps
`raw_*` level values, the multiplier and the evidence reference, then writes
normalized values in VND/share and shares. It never assumes `1000`, and a
multiplier without an evidence reference remains blocked.

To reprocess immutable raw data with an approved policy:

```bash
PYTHONPATH=src python -m data.pipeline data/raw/ws/YYYY-MM-DD.jsonl \
  --price-multiplier 1 --quantity-multiplier 1 \
  --unit-evidence-ref SSI-TICKET-OR-DOC \
  --price-unit VND_PER_SHARE --quantity-unit SHARES \
  --allowed-phase LO
```

Do not run this command with guessed values; the existing raw JSONL remains the
source of truth and can be reprocessed after SSI confirms the convention.

## Troubleshooting

- `CONFIG_REQUIRED`: fill all three SSI credential values.
- HTTP 401: API key/secret/token invalid or expired.
- HTTP 403: key lacks required Market Data/stream scope.
- HTTP 429: wait for `X-RATELIMIT-RESET`; do not retry aggressively.
- `SSLCertVerificationError`: keep verification enabled. Leave `SSI_CA_BUNDLE` blank to use `certifi`, or configure a trusted PEM CA file.
- Connected/subscribed but zero quote: verify that the run is inside the trading session; do not mark W2 accepted.
- WebSocket disconnect: ensure `wss://stream.ssi.com.vn/ws/v3` is reachable and allow SDK heartbeat/reconnect/re-subscribe.
