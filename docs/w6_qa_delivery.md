# W6 — QA / Kiểm thử SSI và tài chính

## Nguyên tắc nghiệm thu

- Không xóa test tài chính W4; các fixture vẫn mang `SYNTHETIC_TEST` và chỉ
  được báo `PASS_SYNTHETIC`.
- Kiểm thử SSI integration chỉ được báo PASS khi có raw evidence thật. Test
  SDK hiện dùng fake client/stream để kiểm tra logic an toàn, không phải bằng
  chứng quyền truy cập production.
- Không test nào khởi tạo Trading client hoặc gửi lệnh.

## Ma trận W6

| Trường hợp | Bằng chứng | Kết quả |
|---|---|---|
| Thiếu API key/secret/client ID | `test_missing_credentials_are_blocked_before_network` | PASS_SYNTHETIC |
| HTTP 401/403/429 | `_error_info` chỉ ghi type/status, không lộ message | PASS_SYNTHETIC |
| Token metadata/refresh | `test_token_metadata_and_refresh_never_return_secret_values` | PASS_SYNTHETIC |
| WebSocket mất kết nối/reconnect | fake stream phát `reconnected`; callback ghi status | PASS_SYNTHETIC |
| Subscribe lại quote/market flag | reconnect callback gọi lại cả hai subscription | PASS_SYNTHETIC |
| Quote thiếu level | partial snapshot, null level, không forward-fill | PASS_SYNTHETIC |
| Sai đơn vị | `UNVERIFIED` khóa eligibility và mô phỏng | PASS_SYNTHETIC |
| SSI bị ghi nhầm NEO | provider/source sai tạo quality flags và invalid book | PASS_SYNTHETIC |
| Timestamp cũ nhưng LIVE | `STALE` flag và eligibility bị từ chối | PASS_SYNTHETIC |
| Không đủ khối lượng | filled/unfilled/coverage, không tạo level 4 | PASS_SYNTHETIC |
| Restart collector/replay | reopen SQLite rồi process lại không nhân đôi quote | PASS_SYNTHETIC |

## Chạy kiểm thử

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Kết quả hiện tại: `71 passed`. Kho canonical có 320.102 LIVE quotes của 201
mã trên 3 ngày. Đơn vị giá/khối lượng đã xác minh; 35.460 snapshot có phase
hợp lệ và mở W4, 284.642 snapshot thiếu phase chỉ dùng quan sát. Coverage đã
ghi 3.113 khoảng thiếu/downtime trên 205 symbol-session rows; replay hoạt động
trên cả 3 ngày. Còn phải thu 2 ngày giao dịch thật để đạt mục tiêu 5 ngày;
fixture vẫn mang `PASS_SYNTHETIC` và không được dùng thay bằng chứng này.
