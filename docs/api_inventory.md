# W1.04 — SSI FastConnect API Inventory

**Phiên bản:** 2.0 — SSI-only  
**Ngày đối chiếu:** 09/11/2026  
**Phạm vi:** Authentication + Market Data REST + Quote Streaming, read-only.

## 1. Môi trường

| Thành phần | Production | Trạng thái trong dự án |
|---|---|---|
| REST base URL | `https://api.ssi.com.vn` | CONFIGURED |
| Market stream | `wss://stream.ssi.com.vn/ws/v3` | CONFIGURED |
| Developer Portal | `https://developers.ssi.com.vn` | DOCUMENTED |
| Credential | Client ID, API Key, API Secret | CONFIGURED_LOCALLY; never documented |

UAT dùng bộ key riêng và chỉ dùng khi SSI cấp thông tin. Không tự đổi production key sang UAT. Nguồn: [SSI environments](https://developers.ssi.com.vn/docs/getting-started/terms-and-environments).

## 2. Authentication

### `POST /api/v3/auth/token`

Request Market Data:

```json
{"apiKey":"<secret>","apiSecret":"<secret>"}
```

- Không truyền `otp` hoặc `transactionId`; hai trường này không cần cho truy vấn dữ liệu.
- Response có `tokenType`, `accessToken`, `expiresAt`, `refreshToken`, `refreshExpiresAt`.
- Token/secret không được ghi raw, log, report hoặc screenshot.
- SDK `Auth.authenticate()` quản lý token; LiquidityGuard chỉ giữ đối tượng auth trong bộ nhớ.

Nguồn: [SSI auth-token](https://developers.ssi.com.vn/docs/api-reference/auth-token).

## 3. Market Data REST dùng trong MVP

Các call được thực hiện qua `ssi-sdk` và Bearer token:

| SDK method | API path/nhóm | Mục đích | Dùng làm L3 snapshot? |
|---|---|---|---|
| `get_securities_info(symbol)` | Securities Info | Metadata mã, sàn, tên, lot size | Không |
| `get_securities_summary(symbol)` | `/api/v3/data/securitiesSummary` | Summary giao dịch hiện tại | Không |
| `get_master_data()` | `/api/v3/data/masterdata` | Giá trần/sàn/tham chiếu | Không |
| `ohlc(symbol, timeframe, from_date, to_date)` | `/api/v3/data/ohlc` | OHLCV lịch sử: giá, volume, value, biến động | Không |

Master Data hỗ trợ `from`, `to`, `pageIndex`, `pageSize`; response phân trang có `pagesCount`, `itemsCount`, `data`. Dữ liệu thiếu phải giữ `null`, không đổi thành 0. Nguồn: [Master Data API](https://developers.ssi.com.vn/docs/api-reference/data-masterData) và [Python MarketDataService](https://developers.ssi.com.vn/docs/sdk/python/service-classes).

REST chỉ cung cấp reference/summary trong thiết kế MVP. Order book ba mức phải đến từ Quote Streaming.

`/api/v3/data/ohlc` hỗ trợ `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `1d`. Daily
được dùng cho lịch sử 5 năm; intraday 1 phút chỉ được yêu cầu trong cửa sổ
SSI cho phép (hiện tài liệu SSI mô tả khoảng gần nhất), không dùng OHLC để tái
dựng bid/ask depth.

## 4. Quote Streaming

### Kết nối

- URL SDK mặc định: `wss://stream.ssi.com.vn/ws/v3`.
- Tạo `Stream(auth)`, gắn callback trước `connect()`.
- Chỉ subscribe `subscribe_symbol_quote(symbols)` và `subscribe_market_flag()`.
- `unsubscribe_all()` và `disconnect()` khi kết thúc.
- SDK hỗ trợ heartbeat, auto-reconnect và re-subscribe; collector vẫn phải ghi trạng thái kết nối.

### Topic và message

| Subscription | Topic logic | Message | Trường dùng |
|---|---|---|---|
| `subscribe_symbol_quote(["SSI","HPG"])` | `quote.<symbol>` | `QuoteMessage` | `type`, `trading_time`, `symbol`, bid/ask price/volume arrays |
| `subscribe_market_flag()` | `market.flag` | `MarketFlagMessage` | `board`, `trading_time`, `flag` |

`QuoteMessage` được ánh xạ:

| SSI | Canonical |
|---|---|
| `bid_prices[0..2]` | `bid_price_1..3` |
| `bid_volumes[0..2]` | `bid_qty_1..3` |
| `ask_prices[0..2]` | `ask_price_1..3` |
| `ask_volumes[0..2]` | `ask_qty_1..3` |
| `trading_time` | `provider_timestamp_raw` / `quote_time_vn` |

Nguồn: [SSI Python streaming services](https://developers.ssi.com.vn/docs/sdk/python/service-classes) và [SSI SDK models](https://developers.ssi.com.vn/docs/sdk/python/utilities).

## 5. Rate limit và lỗi

| Tình huống | Xử lý |
|---|---|
| 400 | Sai request/config; không retry mù |
| 401 | Refresh/re-auth một lần có kiểm soát; không in token |
| 403 | Dừng; kiểm tra scope/key |
| 429 | Đọc `X-RATELIMIT-RESET`, chờ rồi mới thử lại |
| 5xx/timeout | Retry hữu hạn với backoff |
| WS disconnect | Ghi offline, auto-reconnect hữu hạn, xác minh subscription |
| Không có quote | Kiểm tra giờ giao dịch, symbol, scope stream và subscription list |

Hạn mức là theo API key/endpoint và được trả qua `X-RATELIMIT-LIMIT`, `X-RATELIMIT-REMAINING`, `X-RATELIMIT-RESET`; không giả định một con số cố định.

## 6. Read-only allow-list

Được phép:

- `auth.authenticate`
- `data.securities_info`
- `data.securities_summary`
- `data.master_data`
- `stream.quote`
- `stream.market_flag`

Bị cấm: Trading client, OTP, account/portfolio/order subscription, place/amend/cancel/batch/FCO và mọi operation không có trong allow-list.

## 7. Trạng thái bằng chứng

| Hạng mục | Trạng thái | Bằng chứng cần |
|---|---|---|
| Endpoint/SDK mapping | DOCUMENTED | Tài liệu SSI + SDK 3.3.x |
| Unit/fixture | PASS_SYNTHETIC | Test suite |
| Auth thực | PASS | Redacted report, refresh capability; không lưu token |
| REST raw | PASS_LIVE | VPB/FPT info/summary + master data JSONL |
| WSS connection/subscription | PASS | TLS verified; VPB/FPT quote + market.flag listed |
| Quote raw | PENDING_LIVE | Sau giờ giao dịch chưa có `QuoteMessage` |
| Market phase join | PENDING_VERIFY | Quote + MarketFlag cùng phiên/sàn |
| Price/quantity units | VERIFIED_2026-11-19 | SSI support: giá VND, khối lượng cổ phiếu, complete latest book; evidence reference lưu trong policy |

Không nâng trạng thái LIVE chỉ dựa trên test hoặc fixture.
