# W3 Storage Design — SSI

## Luồng dữ liệu giữ nguyên

`raw → processed → mart → replay` là bốn tầng tách biệt. Không tầng nào được sửa ngược dữ liệu của tầng trước.

| Tầng | Vị trí | Vai trò | Quy tắc lịch sử |
|---|---|---|---|
| Raw | `data/raw/rest/`, `data/raw/ws/` | JSONL envelope nguyên bản | append-only; không overwrite |
| Processed | `data/processed/quotes.sqlite` | bảng `quotes` canonical L3 | `quote_id` primary key; chạy lại idempotent |
| Mart | `data/mart/liquidity.sqlite` | bảng `liquidity_metrics` phục vụ W4 | dẫn xuất từ canonical; không thay canonical |
| Replay | `ReplayService` | view tuần tự theo thời gian | chỉ relabel kết quả thành `REPLAY`; giữ `original_source_mode` |

`data/runtime/collector_status.json` chỉ là trạng thái vận hành, không phải lịch sử quote.

## Identity, dedup và cập nhật từng phần

- `raw_event_id` nhận diện một event bất biến. Cùng ID và cùng hash là retry duplicate.
- Cùng `raw_event_id` nhưng khác hash là collision và phải báo lỗi, không được âm thầm bỏ.
- Hai event cùng symbol, cùng giây hoặc cùng payload hash vẫn được giữ nếu ID khác.
- `quote_id` được tạo xác định từ raw lineage nên chạy pipeline nhiều lần không nhân đôi hàng.
- `PARTIAL_BOOK` được lưu đúng như nhận được với null ở level thiếu. Chính sách `PRESERVE_NO_MERGE` cấm lấy level cũ bù vào vì chưa có sequence/delta semantics đủ tin cậy.

## Schema và chỉ mục

Processed giữ cả JSON canonical và các cột lọc: provider, source, mode, symbol, receive/provider time, connection/sequence, update type, completeness và quality state. Các chỉ mục hỗ trợ `(symbol, received_at_utc)`, `(provider, source, source_mode)` và `(connection_id, sequence_no)`.

Mart dùng `quote_id` làm primary key và lưu spread, mid, spread %, bps, depth, notional và OBI. Chỉ canonical quote vượt eligibility gate mới có metric tài chính; hàng không đạt vẫn được lưu cùng rejection reasons để audit.

## Ranh giới OHLC

REST master data và OHLC có thể lưu raw cho mục đích khác nhưng không được normalize thành `quotes_l3`, không được tính coverage L3 và không được dùng để dựng spread/depth/OBI lịch sử. Các chỉ số này cần QuoteMessage tương ứng theo thời gian.
