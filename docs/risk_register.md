# W1.08 — Risk Register (SSI-only)

**Phiên bản:** 2.0  
**Thang điểm:** P/I 1–5; Score = P × I. 1–5 thấp, 6–10 trung bình, 12–15 cao, 16–25 rất cao.

| ID | Rủi ro | P | I | Score | Dấu hiệu | Phòng ngừa | Ứng phó | Owner |
|---|---|---:|---:|---:|---|---|---|---|
| R01 | Chưa đăng ký/kích hoạt API Key SSI | 4 | 5 | 20 | `CONFIG_REQUIRED`, không có key | Đăng ký Developer Portal sớm; tách key Market Data | Chỉ chạy fixture/replay, không tuyên bố LIVE | W2 |
| R02 | Key thiếu quyền Quote Streaming | 4 | 5 | 20 | Auth/REST pass nhưng subscribe không có quote hoặc 403 | Kiểm tra scope và subscription list | Ghi blocker, liên hệ SSI với evidence đã redaction | W2 |
| R03 | API key/secret/token hết hạn hoặc lộ | 3 | 5 | 15 | 401, security alert | `.env`, redaction, rotate, không log token | Revoke/rotate; quét repo/log; dừng LIVE | W2/W6 |
| R04 | QuoteMessage thiếu level hoặc không phải snapshot hoàn chỉnh | 4 | 5 | 20 | Array <3 hoặc thay đổi rời rạc | Lưu raw sequence; xác minh semantics | `UNKNOWN/PARTIAL`; khóa W4 | W2/W3 |
| R05 | Sai đơn vị giá/khối lượng | 4 | 5 | 20 | Notional lệch bảng giá | Mặc định `UNVERIFIED`; đối chiếu tài liệu/raw | Không hiển thị VND notional; khóa simulation | W2/W3/W4 |
| R06 | Thiếu/trễ `trading_time` hoặc timezone mơ hồ | 3 | 4 | 12 | Timestamp null/không parse | Lưu provider raw + receive UTC | Dùng receive time chỉ như observed time; flag | W3 |
| R07 | MarketFlag không ghép đúng quote/sàn | 3 | 5 | 15 | Phase null hoặc phase sai thời điểm | Join theo board/time có test | `MISSING_MARKET_PHASE`; không mô phỏng | W3/W4 |
| R08 | Dữ liệu thiếu, null, sai kiểu hoặc array length khác | 4 | 4 | 16 | Parser/validation flag | Schema-tolerant parser; raw bất biến | N/A + quality flag; không ép 0 | W3 |
| R09 | Disconnect/stale nhưng UI vẫn ghi LIVE | 3 | 5 | 15 | heartbeat/last message quá ngưỡng | Collector status + stale threshold | Khóa LIVE; chuyển replay có nhãn | W2/W5 |
| R10 | Vượt rate limit SSI | 3 | 4 | 12 | HTTP 429 | Đọc rate headers; ưu tiên WS | Chờ reset; backoff; giảm polling | W2 |
| R11 | Callback stream xử lý chậm, mất message | 3 | 5 | 15 | Queue tăng, sequence gap | Callback ngắn, ghi/queue; analytics tách luồng | Ghi gap/downtime; giảm symbols | W2/W3 |
| R12 | Không có dữ liệu ngoài giờ giao dịch | 4 | 2 | 8 | WS connected nhưng 0 quote | Kiểm tra trong phiên; ghi giờ chạy | Không gọi là lỗi auth; dùng replay cho demo | W2/W7 |
| R13 | Không đủ phiên dữ liệu để phân tích thời gian | 3 | 4 | 12 | Coverage <5 phiên | Khởi động collector sớm | Hạn chế claim; báo coverage thực | W2/W3 |
| R14 | Duplicate/reconnect làm nhân đôi record | 3 | 4 | 12 | Hash/event lặp | sequence/hash + deterministic quote ID | Deduplicate retry, giữ update hợp lệ | W3 |
| R15 | Gọi nhầm Trading/OTP/account API | 1 | 5 | 5 | Request ngoài allow-list | Không import Trading; read-only guard | Dừng app/audit; rotate key nếu cần | W2/W6 |
| R16 | Công thức W4 sai hoặc partial fill sai | 3 | 5 | 15 | Không khớp ví dụ tính tay | Decimal, invariants, regression tests | Khóa output; sửa/test lại | W4/W6 |
| R17 | Demo phụ thuộc mạng/credential | 4 | 4 | 16 | SSI unavailable | Chuẩn bị replay redacted | Demo replay có nhãn, nói rõ LIVE status | W5/W7 |
| R18 | Thay provider không được phản ánh trong rubric | 3 | 5 | 15 | Tài liệu còn yêu cầu nguồn cũ | Ghi quyết định chấp thuận trong W1.03 | Không nộp cho tới khi traceability review | W1/W7 |
| R19 | Schema SSI/SDK thay đổi | 3 | 4 | 12 | Test fail, field/method đổi | Pin `ssi-sdk<4`, contract version | Nâng version, fixture/test/migration note | W2/W3 |

## Ưu tiên xử lý

1. R01 — API Key SSI.
2. R02 — quyền Quote Streaming.
3. R04 — full/partial snapshot semantics.
4. R05 — price/quantity units.
5. R08 — dữ liệu thiếu/sai kiểu.
6. R18 — bằng chứng chấp thuận thay provider.

## Quy tắc escalation

- Score ≥16: báo ngay và khóa claim/tính năng liên quan.
- Không retry liên tục 401/403/429.
- Không đổi synthetic/replay thành LIVE.
- Không bỏ quality flag để buộc W4 chạy.
- Schema thực tế khác contract: giữ raw, mở issue, tăng version; không sửa raw.
- Bất kỳ dấu hiệu Trading API: dừng tiến trình và audit trước khi chạy lại.
