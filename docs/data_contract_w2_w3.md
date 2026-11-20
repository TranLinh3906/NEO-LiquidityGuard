# W1.05 — Data Contract W2 ↔ W3

**Contract version:** 2.1  
**Provider duy nhất:** SSI  
**Nguyên tắc:** raw bất biến; canonical có version; không suy diễn field thiếu.

## 1. Phân biệt provider, source, mode và transport

| Field | Ý nghĩa | Giá trị hợp lệ hiện tại |
|---|---|---|
| `provider` | Tổ chức cung cấp dữ liệu | `SSI` |
| `source` | Hệ thống/API nguồn | `SSI_FASTCONNECT` |
| `mode` | Tính chất bằng chứng | `LIVE`, `REPLAY`, `SYNTHETIC_TEST` |
| `transport` | Cơ chế nhận | `REST`, `WS` |
| `endpoint_or_channel` | Endpoint/topic logic | path `/api/v3/...`, `quote`, `market.flag` |

Không dùng `source` để suy ra `mode`. Chỉ collector có kết nối thật và nhận được payload mới tạo raw `mode=LIVE`. Replay không sửa raw/canonical; kết quả đọc có `source_mode=REPLAY` và `original_source_mode` giữ nhãn gốc.

## 2. Raw Event Envelope

| Field | Type | Required | Rule |
|---|---|---:|---|
| `schema_version` | string | Yes | Version envelope |
| `raw_event_id` | UUID/string | Yes | Unique mỗi event |
| `provider` | string | Yes | `SSI` |
| `source` | string | Yes | `SSI_FASTCONNECT` |
| `mode` | enum | Yes | LIVE/REPLAY/SYNTHETIC_TEST |
| `transport` | enum | Yes | REST/WS |
| `endpoint_or_channel` | string | Yes | Endpoint/topic đã allow-list |
| `symbol_hint` | string/null | No | Uppercase nếu biết |
| `received_at_utc` | ISO-8601 UTC | Yes | Clock collector, timezone-aware |
| `provider_timestamp_raw` | string/null | No | Giữ nguyên `trading_time` |
| `connection_id` | string/null | WS | ID phiên stream, không phải credential |
| `sequence_no` | integer/null | WS | Tăng trong connection |
| `http_status` | integer/null | REST | HTTP status |
| `payload` | JSON | Yes | Payload đã redaction, không rename |
| `payload_hash` | SHA-256/string | Yes | Hash payload sau redaction |

Ví dụ synthetic:

```json
{
  "schema_version": "2.0-draft",
  "raw_event_id": "evt-synthetic-ssi-001",
  "provider": "SSI",
  "source": "SSI_FASTCONNECT",
  "mode": "SYNTHETIC_TEST",
  "transport": "WS",
  "endpoint_or_channel": "quote",
  "symbol_hint": "SSI",
  "received_at_utc": "2026-11-09T03:00:00.000Z",
  "provider_timestamp_raw": "2026-11-09T10:00:00+07:00",
  "connection_id": "synthetic-session",
  "sequence_no": 1,
  "payload": {
    "type": "quote",
    "symbol": "SSI",
    "trading_time": "2026-11-09T10:00:00+07:00",
    "bid_prices": [30000, 29950, 29900],
    "bid_volumes": [1000, 800, 600],
    "ask_prices": [30050, 30100, 30150],
    "ask_volumes": [900, 1100, 1200]
  }
}
```

## 3. Canonical `quotes_l3`

### Identity và lineage

- `quote_id`: deterministic UUID từ `raw_event_id`, payload index và symbol.
- `raw_event_id`: bắt buộc, truy ngược raw.
- `provider=SSI`, `source=SSI_FASTCONNECT`.
- `source_type=WS`; `source_mode` lấy trực tiếp từ raw `mode`, replay override thành `REPLAY` khi đọc.
- `schema_version`, `normalization_version`, `payload_hash`.
- `connection_id`, `sequence_no`, `endpoint_or_channel` để kiểm tra mất đoạn và thứ tự phiên.

### Book fields

- `symbol`.
- `bid_price_1..3`, `bid_qty_1..3`.
- `ask_price_1..3`, `ask_qty_1..3`.
- `price_unit`, `quantity_unit` mặc định `UNVERIFIED`.
- Hệ số `price_multiplier_to_vnd` và `quantity_multiplier_to_shares` chỉ được
  dùng khi có `unit_evidence_ref`; giá trị raw vẫn được giữ ở `raw_*`.
- Decimal price; integer non-negative quantity; null khi thiếu/không hợp lệ.

### Time fields

| Field | Nguồn | Quy tắc |
|---|---|---|
| `received_at_utc` | collector | Bắt buộc, UTC |
| `quote_time_vn` | SSI `trading_time` | Giữ timezone; chuẩn hóa Asia/Ho_Chi_Minh khi parse được |
| `time_source` | pipeline | `PROVIDER` hoặc `UNKNOWN` |
| `market_phase_raw` | MarketFlag join | Giữ nguyên flag SSI |
| `market_phase` | verified mapping | Chỉ set khi join được xác minh |
| `market_phase_source` | collector | `SSI_MARKET_FLAG` hoặc `UNKNOWN` |
| `market_phase_board` | SSI `market.flag.b` | Không suy đoán từ mã |
| `market_phase_received_at` | collector | Thời điểm nhận cờ, dùng để truy vết |
| `arrival_delay_seconds` | W3 derived | `received_at_utc - quote_time_vn`; chỉ dùng khi parse được cả hai |

Provider time và receive time không thay thế lẫn nhau. Không gắn `time_source=PROVIDER` nếu timestamp chỉ là clock collector.

## 4. Mapping QuoteMessage

| SSI field | Canonical field | Null/length policy |
|---|---|---|
| `symbol` | `symbol` | Thiếu → invalid |
| `bid_prices[i]` | `bid_price_{i+1}` | Array <3 → incomplete |
| `bid_volumes[i]` | `bid_qty_{i+1}` | Null/negative/fraction → flag |
| `ask_prices[i]` | `ask_price_{i+1}` | Array <3 → incomplete |
| `ask_volumes[i]` | `ask_qty_{i+1}` | Null/negative/fraction → flag |
| `trading_time` | `quote_time_vn` | Thiếu → `MISSING_PROVIDER_TIME` |

REST securities/master data được lưu raw nhưng không normalize thành `quotes_l3`.

Không dùng OHLC lịch sử để tạo các level bid/ask. OHLC không phải snapshot sổ lệnh và không được tính vào coverage, replay L3 hoặc mart spread/depth/OBI.

## 5. Completeness và trạng thái xác minh

`snapshot_completeness`:

- `COMPLETE`: cả bốn arrays có ít nhất 3 phần tử và semantics của QuoteMessage đã được chấp thuận cho L3.
- `UNKNOWN`: thiếu level hoặc chưa đủ bằng chứng semantics.
- `PARTIAL`: dùng khi evidence chứng minh message là delta/partial.

`update_type=FULL_BOOK` khi cả bốn array có ít nhất ba phần tử, ngược lại là `PARTIAL_BOOK`. Mọi partial record dùng `partial_update_policy=PRESERVE_NO_MERGE`: lưu phần quan sát được, để null phần thiếu, không forward-fill từ quote trước.

Trạng thái field/assumption:

- `VERIFIED`: có tài liệu SSI hoặc raw LIVE đối chiếu được.
- `OBSERVED`: thấy trong raw nhưng chưa có xác nhận semantics/unit.
- `UNVERIFIED`: chưa đủ bằng chứng; khóa notional/simulation liên quan.
- `NOT_APPLICABLE`: không áp dụng cho loại record.

## 6. Quality flags tối thiểu

- `MISSING_SYMBOL`, `MISSING_PROVIDER_TIME`.
- `MISSING_BID_LEVEL`, `MISSING_ASK_LEVEL`.
- `NON_NUMERIC_BID_PRICE`, `NON_NUMERIC_ASK_PRICE`, `INVALID_QTY`.
- `INVALID_BID_LEVEL_ORDER`, `INVALID_ASK_LEVEL_ORDER`.
- `CROSSED_OR_LOCKED_BOOK`.
- `UNKNOWN_PRICE_UNIT`, `UNKNOWN_QTY_UNIT`.
- `UNKNOWN_SNAPSHOT_SEMANTICS`, `MISSING_MARKET_PHASE`, `OUTSIDE_ALLOWED_PHASE`.
- `STALE`, `DUPLICATE_RETRY` ở các bước tương ứng.

## 7. Eligibility cho W4

Chỉ `is_simulatable=true` khi: book structurally valid; 3 mức hoàn chỉnh; price/quantity unit verified; phase thuộc allow-list (MVP: `LO` sau xác minh); không stale; mode hiển thị rõ; không có crossed/locked book.

## 8. Idempotency và thay đổi schema

- Retry duplicate: chỉ cùng `raw_event_id` và cùng `payload_hash` mới được bỏ trong một lượt đọc. ID trùng nhưng hash khác là collision lỗi. Hash trùng với ID khác chỉ là tín hiệu QA.
- Insert canonical dùng `quote_id` deterministic để chạy lại không nhân đôi.
- Thay đổi mapping/field tăng contract version, cập nhật fixture, test, dictionary và W4 eligibility.

## 9. Coverage, quality và replay

- Coverage nhóm theo ngày giao dịch và symbol, báo first/last quote, observed span, số gap >60 giây, max gap, phase, mode và số full/partial record.
- `coverage_status=OBSERVED_ONLY`; không tự kết luận đủ cả phiên chỉ từ first/last timestamp.
- Quality report dùng nhãn gốc trong storage, thống kê missing, stale, partial, provenance error, flags và repeated hash.
- Replay hỗ trợ symbol/time range và `live_only`; replay synthetic giữ `original_source_mode=SYNTHETIC_TEST` nên không thể bị trình bày thành bằng chứng LIVE.
