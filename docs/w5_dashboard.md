# W5 — SSI LiquidityGuard Dashboard

Ứng dụng Streamlit nằm tại `src/app/dashboard.py`. Đây là giao diện chỉ đọc,
không khởi tạo Trading client và không có thao tác đặt/sửa/hủy lệnh.

## Chạy

```bash
python -m pip install -e '.[app]'
PYTHONPATH=src streamlit run src/app/dashboard.py
```

Giao diện cung cấp:

- toàn bộ danh mục mã cổ phiếu HOSE/HNX/UPCoM mới nhất từ SSI masterdata; lọc thị trường,
  tìm mã và lọc nhóm ngành;
- chọn chế độ `LIVE`/`REPLAY`/`SYNTHETIC_TEST`, BUY/SELL và khối lượng;
- hiển thị provider/source SSI, trạng thái collector, số bản tin và timestamp;
- KPI spread tuyệt đối/bps, bid depth, ask depth và OBI;
- Bid/Ask Balance, Cumulative Order Book, Sweep Allocation, Coverage Curve,
  VWAP Price Impact, OBI Timeline, Spread Timeline và Bid/Ask Depth Timeline;
- mô phỏng fill, unfilled, coverage, VWAP, slippage và cảnh báo vượt depth;
- Risk Radar, Data Trust và nhãn rõ dữ liệu synthetic, replay và live đã lưu;
- nút khóa `snapshot_id` để WebSocket cập nhật mới không trộn vào một lần tính.
- FinTech workspace theo palette `Deep Plum`, `Dusty Lavender`, `Soft Lilac`,
  `Warm Sand`, `Cream Beige`, `Blush Pink`; có Global Control Bar, Quick Tasks,
  Watchlist, Session Snapshot và Brand Palette.
- Historical OHLCV panel cho giá, volume, value, price change và so sánh thanh
  khoản; 1m bars được gom theo khung 30 phút để tìm vùng thanh khoản cao/thấp.
- Cấp dữ liệu A/B/C: catalog toàn bộ mã, watchlist LIVE 10–50 mã, và toàn thị
  trường chỉ hiển thị như capability bị khóa chờ SSI cấp quyền/kiểm chứng hiệu năng.

`LIVE` chỉ đọc canonical `source_mode=LIVE` đã được collector lưu. Nếu chưa có
QuoteMessage SSI thật, ứng dụng báo “chưa có quote” và không dùng REST/OHLC để
thay thế lịch sử sổ lệnh ba mức. `SYNTHETIC_TEST` dùng fixture trong
`data_sample/` qua SQLite in-memory, không làm thay đổi kho dữ liệu.

Market Pulse đã mở rộng thành bảng toàn thị trường: 1.517 cổ phiếu trong
2.179 mã SSI, có lọc loại mã/sàn/ngành, tìm theo tên/mã/ngành và ẩn mã chưa có
giao dịch. Tên doanh nghiệp và ngành ICB lấy từ SSI `securitiesByBoard`;
`masterdata` cung cấp metadata tham chiếu. Có 1.192 mã với dữ liệu tổng hợp
trong lần thu 11–18/11/2026; 325 mã trả rỗng được giữ rõ trạng thái.
Xem `docs/universe_catalog.md` để biết số liệu, nguồn và giới hạn hiện tại.
