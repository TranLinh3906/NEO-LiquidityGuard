# W1.02 — Phạm vi MVP LiquidityGuard

**Phiên bản:** 2.0 — SSI-only  
**Ngày cập nhật:** 09/11/2026  
**Quyết định kiến trúc:** Phương án A — SSI FastConnect là nguồn dữ liệu duy nhất.

## 1. Mục tiêu sản phẩm

LiquidityGuard là công cụ read-only giúp người dùng quan sát thanh khoản hiển thị trên ba mức bid/ask, tính spread, depth, OBI và mô phỏng BUY/SELL giả định. Sản phẩm không đặt lệnh, không dự báo giá và không đưa ra khuyến nghị đầu tư.

SSI FastConnect cung cấp toàn bộ dữ liệu đầu vào:

- Authentication bằng API Key/API Secret để lấy Market Data token, không truyền OTP.
- REST Market Data để lấy thông tin mã, summary và master data.
- WebSocket Quote Streaming để nhận `QuoteMessage` và `MarketFlagMessage`.
- Raw JSONL, canonical SQLite và replay do LiquidityGuard quản lý cục bộ.

## 2. Quyết định thay nguồn dữ liệu

- Chấp thuận thay nguồn API nêu trong đề gốc bằng SSI FastConnect.
- Không duy trì adapter, credential, endpoint, test hoặc runbook của nhà cung cấp cũ.
- Giá trị sản phẩm, công thức W4, user stories và nguyên tắc an toàn không đổi.
- Bằng chứng LIVE chỉ hợp lệ khi có raw SSI được thu từ API Key có quyền tương ứng.
- Fixture luôn mang `mode=SYNTHETIC_TEST`; replay luôn trả `mode=REPLAY`.

## 3. Phạm vi P0

| ID | Chức năng | Nguồn/đầu ra | Điều kiện chấp nhận |
|---|---|---|---|
| F01 | Xác thực read-only | `POST /api/v3/auth/token` | Không OTP; không log token/secret |
| F02 | Danh mục mã | `get_securities_info`, theo mã/chỉ số/sàn khi mở rộng | Symbol có nguồn và trạng thái null rõ ràng |
| F03 | Dữ liệu tham chiếu | securities summary + master data | Lưu raw; không dùng REST summary làm order-book snapshot |
| F04 | Quote streaming | `subscribe_symbol_quote` / topic `quote.*` | Lưu từng `QuoteMessage` với sequence và receive time |
| F05 | Phiên thị trường | `subscribe_market_flag` / `market.flag` | Ghép phase theo board/thời gian có quy tắc; không tự suy diễn |
| F06 | Raw storage | JSONL append-only | Có provider/source/mode/transport/timestamp/hash |
| F07 | Canonical L3 | SQLite quote schema | 3 giá + 3 KL mỗi phía, flags và raw lineage |
| F08 | KPI | spread, depth, OBI | Chỉ tính khi dữ liệu đủ điều kiện |
| F09 | Simulator | BUY quét ask, SELL quét bid | Tối đa 3 mức; trả partial/unfilled |
| F10 | LIVE/REPLAY | Collector + replay | Không hiển thị replay/synthetic là LIVE |
| F11 | QA | tests + quality/coverage report | Missing/duplicate/type/time/disconnect được kiểm tra |
| F12 | Tài liệu | README, runbook, W1–W4 evidence | Có thể tái chạy, không chứa secrets |

## 4. Phạm vi P1

- So sánh nhiều mã và spread/OBI theo thời gian.
- Subscribe index/board có kiểm soát sau khi đánh giá throughput.
- Xuất kết quả mô phỏng CSV.
- Theo dõi rate-limit headers và thống kê reconnect/downtime.
- Bổ sung dữ liệu trade/OHLCV nhưng không thay quote L3 làm đầu vào mô phỏng.

## 5. Ngoài phạm vi

- Trading REST/WebSocket, OTP, private key, account/portfolio/order topics.
- Đặt, sửa, hủy lệnh; auto-trading; thử lệnh bằng tiền thật.
- Dự báo giá, xác suất khớp, queue position hoặc khuyến nghị mua/bán.
- Ngoại suy order book ngoài ba mức hiển thị.
- Dùng dữ liệu nhà cung cấp khác hoặc hợp nhất nhiều nguồn.
- Tuyên bố dữ liệu hoàn chỉnh khi semantics/snapshot chưa được xác minh.

## 6. User stories giữ nguyên

1. Chọn mã cổ phiếu và thấy nguồn SSI.
2. Xem ba mức bid/ask cùng giá, khối lượng và timestamp.
3. Biết dữ liệu là LIVE, REPLAY hay SYNTHETIC_TEST; biết stale/disconnected.
4. Xem spread, depth, OBI hoặc lý do kết quả là N/A.
5. Mô phỏng BUY/SELL và xem fill theo từng mức.
6. Thấy coverage, VWAP, slippage và unfilled quantity.
7. Replay dữ liệu đã lưu nhưng không bị nhầm là LIVE.

## 7. Luồng nghiệp vụ

1. Đọc cấu hình SSI và chặn khởi động LIVE nếu thiếu credential.
2. Lấy Market Data token không OTP.
3. Thu REST reference data và mở WebSocket Quote/Market Flag.
4. Ghi raw SSI append-only, đã redaction.
5. Chuẩn hóa `QuoteMessage` sang canonical L3; gắn quality flags.
6. Ghép phase đã xác minh; kiểm tra units, freshness và completeness.
7. W4 chỉ tính/mô phỏng nếu eligibility pass.
8. Khi mất kết nối hoặc stale: khóa LIVE simulation và cho phép replay.

## 8. Yêu cầu dữ liệu tối thiểu

- `symbol`, `bid_prices[0:3]`, `bid_volumes[0:3]`.
- `ask_prices[0:3]`, `ask_volumes[0:3]`.
- `trading_time`, `received_at_utc`, `market_phase` khi đã ghép đúng.
- `provider`, `source`, `mode`, `transport`, `raw_event_id`, `payload_hash`.
- `snapshot_completeness`, `price_unit`, `quantity_unit`, `quality_flags`.

Không tự suy ra timestamp, level bị thiếu, unit, market phase hoặc snapshot completeness.

## 9. Yêu cầu phi chức năng

- Secrets chỉ ở `.env`, bị ignore; raw/log không chứa token/API secret.
- Rate limit lấy từ header SSI; HTTP 429 chờ đến `X-RATELIMIT-RESET`.
- Ưu tiên WebSocket cho realtime; không polling dày.
- Callback stream phải ngắn: ghi/đẩy queue, không chạy analytics nặng.
- Timestamp lưu UTC; provider time giữ nguyên và chuẩn hóa sang Asia/Ho_Chi_Minh khi đủ thông tin.
- Mỗi canonical quote truy ngược được raw event.

## 10. Definition of Done

MVP đạt khi có: (1) SSI auth read-only thành công; (2) ít nhất một raw REST SSI; (3) ít nhất một raw `QuoteMessage`; (4) canonical L3 truy vết được; (5) units, phase và snapshot semantics được xác minh hoặc bị khóa đúng; (6) KPI và BUY/SELL/partial-fill pass test; (7) LIVE/REPLAY/stale handling; (8) QA/security report; (9) README/runbook; (10) không có code Trading hoặc dữ liệu synthetic giả danh LIVE.
