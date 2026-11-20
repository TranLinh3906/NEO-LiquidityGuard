# W3 — SSI Data Engineering & Replay

**Trạng thái:** đã thu và canonicalize 320.102 `LIVE` QuoteMessage SSI của
201 mã trên 3 ngày quan sát (16, 18 và 19/11/2026). Từ 19/11/2026, đơn vị giá/khối lượng và
snapshot semantics đã được SSI support xác nhận; dữ liệu canonical được chuẩn
hóa lại với hệ số `1/1` mà không thay đổi raw lineage. Lần
thu có `market.flag` hợp lệ tạo 35.460 snapshot có thể mô phỏng. 284.642 quote
còn lại thiếu cùng-board flag nên phase vẫn `UNKNOWN`; các quote này chỉ dùng
cho biểu đồ quan sát và không được hồi điền theo đồng hồ.

## Đầu việc và sản phẩm

| Mã | Sản phẩm đã làm | Bằng chứng | Trạng thái |
|---|---|---|---|
| W3.02 | Từ điển canonical gồm lineage, time, 12 trường L3, unit, completeness và quality | `docs/data_dictionary.csv` | DONE |
| W3.03 | Mapping `bid_prices/bid_volumes/ask_prices/ask_volumes[0..2]` vào ba mức; hỗ trợ hệ số có bằng chứng và giữ giá trị raw | `src/data/normalize_quotes.py`, `data/processed/quotes.sqlite` | DONE_LIVE / UNIT_VERIFIED |
| W3.04 | Phân loại full/partial; không silent fill; kiểm tra order/crossed/unit/phase và nguồn phase | normalizer + validator + `market_flags.py` | UNIT_AND_BOOK_VERIFIED / PHASE_PER_SNAPSHOT |
| W3.05 | Retry dedup theo immutable event ID; phát hiện ID collision; không xóa update cùng giây | `src/data/deduplicate.py`, tests | DONE |
| W3.06 | SQLite insert idempotent, append-only raw, partial `PRESERVE_NO_MERGE`, mart riêng | `quote_store.py`, `mart.py`, `storage_design.md` | DONE |
| W3.07 | Coverage theo ngày/symbol/mode, cửa sổ phiên kỳ vọng, missing edge và downtime | `coverage_report.py`, `outputs/qa/coverage_report.csv` | DONE_LIVE_OBSERVED; 3/5 ngày, còn thiếu 2 ngày LIVE |
| W3.08 | Replay theo symbol/time và báo cáo replay nhiều ngày LIVE; giữ nhãn gốc | `replay.py`, `outputs/qa/live_replay_report.json` | DONE_LIVE_MULTI_SESSION; hiện có 3 ngày |
| W3.09 | Báo cáo missing, stale, gap, downtime phiên, provenance, repeated hash và quality flags | `quality_report.py`, `outputs/qa/data_quality.json` | DONE_LIVE_OBSERVED; 3.113 gap/downtime theo cửa sổ symbol; unit verified, phase theo từng snapshot |
| W3.10 | Fixture/sample luôn mang `SYNTHETIC_TEST`; replay không che nhãn gốc | sample + label-integrity tests | DONE |

## Quy tắc kỹ thuật bắt buộc

1. Raw JSONL là nguồn sự thật và không overwrite.
2. Canonical chỉ nhận SSI WebSocket quote. REST master data/OHLC được bỏ qua ở bước tạo sổ lệnh.
3. Array đủ ba phần tử mỗi phía được phân loại `FULL_BOOK`; thiếu bất kỳ phần nào là `PARTIAL_BOOK`.
4. Partial record được lưu nguyên trạng, không ghép level cũ. Chỉ được xây cơ chế merge khi SSI cung cấp semantics delta/sequence đủ kiểm chứng.
5. Cùng `raw_event_id` + hash là retry; cùng ID khác hash là lỗi; ID khác thì giữ dù cùng timestamp/hash.
6. `quote_id` và mart primary key giúp chạy lại không mất hoặc nhân đôi lịch sử.
7. Replay là view: storage giữ `LIVE`/`SYNTHETIC_TEST`, kết quả replay thêm `original_source_mode` rồi mới gắn `REPLAY`.
8. Coverage luôn ghi `OBSERVED_ONLY`; không suy diễn đủ phiên từ một vài bản tin.

## Lệnh chạy khi có raw SSI thật

```bash
PYTHONPATH=src python -m data.pipeline data/raw/ws/YYYY-MM-DD.jsonl \
  --price-unit VND_PER_SHARE --quantity-unit SHARES --allowed-phase LO \
  --stale-after-seconds 5
PYTHONPATH=src python -m data.mart
PYTHONPATH=src python -m data.quality_report
PYTHONPATH=src python -m data.coverage_report
PYTHONPATH=src python -m data.replay
```

Unit được truyền theo bằng chứng `SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19`: giá VND, khối lượng cổ phiếu, multiplier `1/1`. Phase vẫn chỉ được truyền khi ghép cùng-board `market.flag`; phase thiếu tiếp tục khóa mô phỏng.

## Điều kiện nghiệm thu LIVE còn thiếu

- Raw `mode=LIVE` có QuoteMessage thực, không chỉ heartbeat/subscription ACK. **Đã đạt: 320.102 canonical quotes, 201 mã quan sát.**
- Đọc lại được canonical L3 với lineage trỏ về raw event.
- Quality/coverage thể hiện đúng symbol, thời gian, gap, full/partial và không lẫn synthetic.
- Replay `live_only=True` trả lại dữ liệu theo thứ tự và giữ `original_source_mode=LIVE`.
- Mart tạo được metric chỉ cho quote vượt eligibility gate.

OHLC lịch sử không thể thay thế điều kiện này: OHLC không chứa đồng thời ba mức giá/khối lượng bid và ask, nên không tái dựng được spread, depth hay OBI theo thời gian.
