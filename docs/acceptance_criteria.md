# W1.07 --- ACCEPTANCE CRITERIA / DEMO SCENARIOS

**Phiên bản:** 1.0 --- Working Draft\
**Ngày:** 07/11/2026\
**Dữ liệu ví dụ:** SYNTHETIC_TEST; không phải quote thị trường thật.

## 1. Nguyên tắc demo

Demo phải phân biệt ba mode: - `LIVE`: dữ liệu nhận trực tiếp từ SSI và
có raw lineage. - `REPLAY`: dữ liệu SSI đã thu thập/lưu trước đó và được
phát lại. - `SYNTHETIC_TEST`: fixture giả định để test công thức hoặc
giao diện.

Không dùng fixture để chứng minh tích hợp SSI thành công. Bằng chứng
LIVE phải có raw event, received timestamp, nguồn, symbol và log kết nối
đã che thông tin nhạy cảm.

## 2. Kịch bản A --- Thị trường bình thường, dữ liệu hợp lệ

**Mục tiêu:** Chứng minh chọn mã, xem book, KPI và mô phỏng BUY thành
công.

Input fixture: - Bid1 29,750 / 100,000 - Bid2 29,700 / 80,000 - Bid3
29,650 / 50,000 - Ask1 29,800 / 60,000 - Ask2 29,850 / 100,000 - Ask3
29,900 / 120,000 - Phase `LO` (synthetic) - Snapshot COMPLETE
(synthetic) - Freshness 1 giây (synthetic) - BUY requested quantity =
100,000

Expected KPI: - Spread absolute = 50. - Mid-price = 29,775. - Spread =
0.167926% ≈ 16.7926 bps. - Bid depth = 230,000. - Ask depth = 280,000. -
OBI = −0.098039.

Expected simulation: \| Level \| Price \| Available qty \| Fill qty \|
\|---\|---:\|---:\|---:\| \| Ask1 \| 29,800 \| 60,000 \| 60,000 \| \|
Ask2 \| 29,850 \| 100,000 \| 40,000 \| \| Ask3 \| 29,900 \| 120,000 \| 0
\|

-   Filled = 100,000.
-   Unfilled = 0.
-   Coverage = 100%.
-   VWAP = 29,820.
-   Slippage absolute = 20.
-   Slippage = 6.7114 bps.
-   UI ghi rõ `SYNTHETIC_TEST` nếu chạy fixture; nếu chạy SSI thật thì
    hiển thị `LIVE` và quote lineage.

Pass khi: - Kết quả khớp expected trong tolerance số học đã thống
nhất. - Có đơn vị. - Hiển thị source mode và timestamp. - Không có lệnh
thật được gửi.

## 3. Kịch bản B --- Khối lượng yêu cầu vượt depth ba mức

**Mục tiêu:** Chứng minh hệ thống không ngoại suy ngoài ba mức.

Dùng cùng order book fixture, BUY requested quantity = 400,000.

Expected: - Ask depth tổng = 280,000. - Filled = 280,000. - Unfilled =
120,000. - Coverage = 70%. - Notional phần filled = 8,361,000,000 theo
giả định giá VND/CP của fixture. - VWAP phần filled = 29,860.7143. -
Slippage so với ask1 = 60.7143; khoảng 20.374 bps. - Kết quả phải hiển
thị cảnh báo "Khối lượng vượt độ sâu ba mức; phần còn lại chưa được mô
phỏng".

Pass khi: - Không có level 4 được tạo. - Không gán giá cho 120,000 chưa
được đáp ứng. - VWAP chia cho filled quantity (280,000), không chia cho
requested quantity (400,000). - Coverage đúng 70%.

Kiểm thử bổ sung: BUY `400` với tổng depth ba mức là `350` phải trả
`filled_qty=350`, `unfilled_qty=50`, coverage `87,5%`; không được ngoại
suy giá cho 50 cổ phiếu còn lại.

## 4. Kịch bản C --- Mất kết nối / dữ liệu stale / Replay

**Mục tiêu:** Chứng minh hệ thống không giả vờ dữ liệu cũ là LIVE.

Setup: - Last received quote lúc 10:00:00. - Thời điểm kiểm tra lúc
10:00:15. - Stale threshold cấu hình = 5 giây. - WS connection =
disconnected. - Có bản ghi raw/processed đã lưu lúc 10:00:00.

Expected LIVE behavior: - Hiển thị `DISCONNECTED` hoặc `STALE`. - Hiển
thị last received time và tuổi dữ liệu 15 giây. - `is_simulatable=false`
cho mode LIVE. - Không cập nhật timestamp giả. - Không hiển thị quote cũ
như mới.

Expected REPLAY behavior: - Người dùng chọn REPLAY và thời điểm
10:00:00. - App đọc đúng record đã lưu. - Nhãn mode vẫn là `REPLAY`. -
Tính toán từ record đó tái lập được. - Không phát sinh request đặt lệnh.

Pass khi: - Trạng thái kết nối và mode rõ ràng. - LIVE stale bị khóa mô
phỏng. - REPLAY hoạt động offline và có nguồn record.

## 5. Kịch bản D --- Giá ATO/ATC hoặc không parse được

Input: - `askPrice1 = "ATO"` hoặc `"ATC"`; các trường raw được giữ
nguyên. Expected: - Parser không chuyển thành 0. - Gắn
`NON_NUMERIC_ASK_PRICE`. - Không mô phỏng BUY nếu ask1 không hợp lệ. -
UI giải thích "Giá ở mức này không phải giá số để mô phỏng trong trạng
thái hiện tại".

## 6. Kịch bản E --- Snapshot partial hoặc unknown

Input: - WS message chỉ có một số trường; chưa xác minh semantics.
Expected: - `snapshot_completeness=UNKNOWN` hoặc `PARTIAL`. -
`is_simulatable=false`. - Không tự điền field thiếu bằng giá/khối lượng
cũ nếu chưa có quy tắc merge đã xác minh. - Lưu raw message để phân
tích.

## 7. Kịch bản F --- Phase ngoài allow-list

Input: - Market phase `ATO`, `ATC`, `PRE`, `PLO`, `C` hoặc trạng thái
chưa mapping. Expected: - Nếu MVP allow-list chỉ `LO`, không mô phỏng. -
UI hiển thị phase raw và lý do từ chối. - Không tự đổi phase lạ thành
`LO`.

## 8. Kiểm chứng theo thời gian và timezone

Vì LiquidityGuard có LIVE/REPLAY và có thể trình bày diễn biến theo thời
gian, collector cần lưu dữ liệu đủ để kiểm chứng. Mục tiêu tối thiểu là
05 phiên giao dịch; ưu tiên 10 phiên trở lên nếu thời gian cho phép. Nếu
thực tế chỉ thu được ít phiên hơn, báo cáo phải nêu số phiên thực có và
không đưa ra kết luận vượt quá mẫu dữ liệu. Mọi timestamp phải được
lưu/trình bày nhất quán theo `Asia/Ho_Chi_Minh` (UTC+7).

## 9. Checklist nghiệm thu theo module

  ------------------------------------------------------------------------------
  ID             Module         Điều kiện pass                Bằng chứng
  -------------- -------------- ----------------------------- ------------------
  AC01           W2             REST/WS auth và nhận dữ liệu  Raw capture + log
                                SSI thật (nếu quyền được cấp) đã che secrets

  AC02           W2             WS Quote subscribe đúng      Subscribe
                                symbol                        request + message
                                                              nhận

  AC03           W3             Raw → canonical có lineage    `raw_event_id`,
                                                              quote record

  AC04           W3             Parser xử lý                  Unit test report
                                number/string/null/ATO/ATC    

  AC05           W4             Spread/depth/OBI đúng ví dụ   Unit tests +
                                tính tay                      output

  AC06           W4             BUY/SELL và partial fill đúng Test report

  AC07           W5             Có ít nhất 3 KPI              Screenshot

  AC08           W5             Có ít nhất 2 trực quan hóa    Screenshot/video

  AC09           W5             Có LIVE/REPLAY/SYNTHETIC_TEST Screenshot và test

  AC10           W6             Có                            QA report
                                stale/invalid/phase/partial   
                                tests                         

  AC11           W6             Không có secrets hoặc lệnh    Security
                                thật                          checklist + code
                                                              review

  AC12           W7             README, báo cáo, demo tái lập File nộp + video
                                được                          
  ------------------------------------------------------------------------------

## 10. Tolerance số học

-   Số lượng cổ phiếu: phải khớp tuyệt đối.
-   Spread/depth: phải khớp chính xác theo input.
-   VWAP: tolerance đề xuất 0.01 đơn vị giá hoặc sai số floating point
    tương đương; ưu tiên Decimal.
-   OBI/percent/bps: tolerance 1e-6 trong unit tests.
-   Giao diện có thể làm tròn để đọc, nhưng test phải dùng giá trị chưa
    làm tròn.

## 11. Demo script gợi ý

1.  Giới thiệu vấn đề: nhìn best bid/ask chưa đủ khi khối lượng lớn.
2.  Chọn một mã; chỉ rõ nguồn và timestamp.
3.  Giải thích ba KPI spread, depth, OBI.
4.  Nhập BUY 100,000: xem đi qua ask1/ask2 và VWAP.
5.  Tăng lên BUY 400,000: xem 120,000 chưa được đáp ứng.
6.  Ngắt WS hoặc phát lại tình huống stale: live bị khóa.
7.  Chuyển REPLAY: xem record đã lưu.
8.  Kết thúc bằng giới hạn: ba mức hiển thị, không phải khớp lệnh thật,
    không đặt lệnh.
