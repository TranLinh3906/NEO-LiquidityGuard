# Báo cáo W7 — LiquidityGuard SSI

**Phiên bản:** W7 / 16-11-2026  
**Phạm vi:** SSI FastConnect Market Data, read-only; không có Trading client và không gửi lệnh.

## 1. Tóm tắt điều hành

LiquidityGuard là công cụ quan sát thanh khoản dựa trên sổ lệnh hiển thị ba
mức. SSI FastConnect đã thay NEO làm nguồn dữ liệu duy nhất trong MVP. Hệ
thống có lớp SSI REST/WebSocket, lưu raw bất biến, canonical quote, replay,
mart tài chính và dashboard Streamlit. Đã thu 415 QuoteMessage LIVE (VPB 126,
FPT 289), lưu và đọc lại thành công. Kết quả tài chính LIVE vẫn bị khóa cho
đến khi xác minh đơn vị và market phase.

## 2. Vấn đề người dùng

Người dùng cần biết một lệnh mua/bán có thể được đáp ứng bao nhiêu trong ba
mức giá đang hiển thị, thay vì chỉ nhìn best bid/ask. Sản phẩm trả lời bằng
spread, depth, OBI, fill, coverage, VWAP và slippage; không dự báo giá, không
thay thế khớp lệnh thật và không đưa khuyến nghị đầu tư.

## 3. Thiết kế sản phẩm

Kiến trúc hiện tại:

```text
SSI REST/WebSocket → raw JSONL → canonical SQLite → liquidity mart → replay/dashboard
```

- REST dùng authentication, securities info/summary và master data.
- WebSocket subscribe `quote.VPB`, `quote.FPT`, `market.flag`.
- `RawWriter` redaction secrets; `QuoteStore` idempotent theo `quote_id`.
- Dashboard tại `src/app/dashboard.py` chỉ đọc dữ liệu đã lưu.
- Trading/FCO/order endpoints bị khóa bởi read-only guard.

## 4. Dữ liệu API

Raw envelope lưu `provider=SSI`, `source=SSI_FASTCONNECT`, `mode`, transport,
endpoint/channel, receive time, provider time, connection/sequence và payload
hash. `QuoteMessage` ánh xạ:

| SSI | Canonical |
|---|---|
| `bid_prices[0..2]` | `bid_price_1..3` |
| `bid_volumes[0..2]` | `bid_qty_1..3` |
| `ask_prices[0..2]` | `ask_price_1..3` |
| `ask_volumes[0..2]` | `ask_qty_1..3` |

Thiếu level được lưu null và gắn `PARTIAL_BOOK`; không lấy level cũ bù vào.
REST/OHLC không được biến thành lịch sử L3.

## 5. Phương pháp tài chính

Giữ nguyên công thức W4:

- spread tuyệt đối, %, bps và mid-price;
- bid/ask depth ba mức và OBI;
- filled, unfilled, coverage;
- VWAP chỉ trên phần fill thực hiện được;
- slippage so với best price.

Eligibility bổ sung kiểm tra provider/source SSI, đơn vị giá/khối lượng,
thứ tự giá, crossed book, snapshot completeness, market phase và stale.
Ví dụ BUY 400 với depth 350 trả coverage 87,5%, unfilled 50 và không tạo
level 4.

## 6. Triển khai sản phẩm

Chạy dashboard:

```bash
python -m pip install -e '.[app]'
PYTHONPATH=src streamlit run src/app/dashboard.py
```

Sidebar cho phép chọn VPB/FPT, `LIVE`/`REPLAY`/`SYNTHETIC_TEST`, BUY/SELL và
khối lượng. Màn hình hiển thị trạng thái SSI, timestamp, bảng book, biểu đồ
depth, biểu đồ giá theo level, KPI và giải thích thiếu thanh khoản. Fixture
được dùng mặc định để demo offline; VPB/FPT sẽ có dữ liệu khi canonical SSI
quote tương ứng tồn tại.

## 7. Kiểm thử

Kết quả tự động hiện tại: **40 passed**. W6 đã bao phủ missing credentials,
401/403/429, token refresh, reconnect/resubscribe, partial/wrong unit, NEO
lineage, stale LIVE, partial fill và restart/replay idempotency.

Bằng chứng SSI thật ngày 16-11-2026: authentication PASS, REST securities
info/master data PASS, WSS TLS/heartbeat/subscription PASS; `quote_count=415`,
`raw_quotes_found=415`, `canonical_quotes_parsed=415`. Strict quote
persistence/readback acceptance đã PASS. Quality flags còn `UNKNOWN_PRICE_UNIT`,
`UNKNOWN_QTY_UNIT` và `MISSING_MARKET_PHASE` trên 415 record.

## 8. Hạn chế

- Quyền API/quote streaming và IP allow-list phụ thuộc SSI.
- Ngoài phiên HOSE có thể không có quote dù auth và subscription thành công.
- Đơn vị giá/khối lượng chỉ được mở tính toán sau khi xác minh.
- Dữ liệu có thể trễ, mất kết nối hoặc partial.
- Chỉ quan sát ba mức; không biết level 4+, queue position, lệnh ẩn, hủy/sửa
  hay khớp lệnh thực.
- OHLC lịch sử không thay thế được lịch sử bid/ask L3.

## 9. Hướng phát triển

Ưu tiên thu đủ nhiều phiên SSI thật, bổ sung giám sát coverage/gap và ảnh
demo LIVE đã redaction. Sau khi MVP SSI ổn định, có thể thêm NEO làm nguồn
thứ hai qua adapter riêng, nhưng phải giữ `provider/source` tách biệt và
không trộn dữ liệu khác nguồn trong cùng một snapshot.

## 10. Kết luận

LiquidityGuard hiện đã có đường đi đầy đủ từ dữ liệu SSI đến chỉ số thanh
khoản, mô phỏng thực hiện và dashboard có thể chạy offline. Giá trị thực tế
là làm rõ chi phí và mức đáp ứng của một lệnh trên phần sổ lệnh đang quan
sát, đồng thời bảo toàn lineage và nói rõ khi dữ liệu chưa đủ để kết luận.

### Tài liệu tham chiếu triển khai

- [W2 SSI delivery](w2_ssi_delivery.md)
- [W3 data engineering](w3_ssi_delivery.md)
- [W5 dashboard](w5_dashboard.md)
- [W6 QA delivery](w6_qa_delivery.md)
- [SSI runbook](ssi_api_runbook.md)
