# W1.03 --- TÓM TẮT ĐỀ THI GỐC VÀ RUBRIC CHÍNH THỨC

> Đây là bản lưu yêu cầu đề gốc, không phải cấu hình hệ thống hiện hành.
> Quyết định W1.03 chấp thuận Phương án A thay nguồn API bằng SSI FastConnect
> được ghi tại `docs/rubric_traceability.csv`. Không dùng endpoint trong tài
> liệu lưu trữ này để vận hành LiquidityGuard.

**Nguồn:** `261BFF401101_261BFF401102_GPMUD1_DETHICUOIKY_DOAN.docx`\
**Học phần:** Gói phần mềm ứng dụng cho tài chính 1 --- Đồ án cá nhân
cuối kỳ\
**Ngày cập nhật hồ sơ W1:** 07/11/2026

Tài liệu này tách rõ yêu cầu đề thi gốc với các quyết định thiết kế nội
bộ của NEO LiquidityGuard.

## 1. Thông điệp cốt lõi của đề

Không bắt đầu từ công nghệ. Phải bắt đầu từ một vấn đề tài chính có
thật, xác định người dùng, sử dụng NEO API làm nguồn dữ liệu/hạ tầng cốt
lõi, sau đó xây dựng sản phẩm có thể chạy, có logic tài chính và có bằng
chứng kiểm chứng.

Đề yêu cầu sinh viên chứng minh: - Xác định vấn đề thực tế và người
dùng. - Thu thập, chuẩn hóa, lưu trữ, khai thác dữ liệu NEO API đúng quy
ước. - Có chỉ báo/mô hình/quy tắc phân tích có cơ sở tài chính. - Có sản
phẩm phần mềm chạy và tương tác. - Có kiểm thử, đánh giá ổn định, trình
bày giới hạn trung thực. - Có bảo mật dữ liệu, quản lý khóa truy cập và
sử dụng API có trách nhiệm.

## 2. Bốn điều kiện tối thiểu của mọi đồ án

1.  **NEO API là thành phần cốt lõi:** dữ liệu/chức năng NEO tạo ra giá
    trị chính, không chỉ để minh họa.
2.  **Có logic tài chính:** tính toán, xếp hạng, cảnh báo, đánh giá, mô
    phỏng, giải thích hoặc hỗ trợ quyết định. Chỉ hiển thị giá/biểu đồ
    là chưa đủ.
3.  **Có sản phẩm chạy được:** người chấm quan sát được luồng nhập dữ
    liệu → xử lý → hiển thị kết quả hoặc xem bản ghi trình diễn đầy đủ.
4.  **Có kiểm chứng:** có bằng chứng sản phẩm hoạt động đúng, dữ liệu xử
    lý hợp lý và kết quả không vượt quá khả năng mô hình.

## 3. Hướng sản phẩm LiquidityGuard đang chọn

Sản phẩm kết hợp trực tiếp các hướng gợi ý trong đề: - Gợi ý số 3: **Bộ
đo thanh khoản cổ phiếu** --- spread, độ sâu sổ lệnh, khả năng hấp thụ
khối lượng. - Gợi ý số 4: **Theo dõi mất cân bằng sổ lệnh** --- khai
thác ba mức bid/ask để đánh giá mất cân bằng cung/cầu ngắn hạn. - Thành
phần mô phỏng có liên hệ với gợi ý số 12: **Trình mô phỏng giao dịch**
--- nhưng MVP chỉ mô phỏng phần thanh khoản hiển thị, không phát sinh
giao dịch thật.

Vì vậy, không nên quảng bá đây là sản phẩm dự báo giá hoặc hệ thống tự
động giao dịch. Giá trị chính là đo thanh khoản ba mức và ước tính tác
động của khối lượng giả định trên phần book quan sát được.

## 4. Yêu cầu NEO API và dữ liệu

  -------------------------------------------------------------------------
  Yêu cầu trong đề        Chuẩn cần đáp ứng         Cách LiquidityGuard đáp
                                                    ứng
  ----------------------- ------------------------- -----------------------
  NEO API là nguồn cốt    NEO là nguồn chính; nguồn Dữ liệu `stockInfo`,
  lõi                     ngoài nếu có phải ghi rõ  `stockDetail`,
                                                    `stockList`,
                                                    `marketStatus` từ NEO

  Mức sử dụng tối thiểu   Ít nhất 01 luồng          Dùng WS `stockInfo` có
                          WebSocket có lưu dữ liệu, lưu raw; đồng thời dùng
                          HOẶC ít nhất 02 nhóm API  các REST group liên
                          liên quan trực tiếp       quan

  Số biến tối thiểu       Ít nhất 03 trường có ý    Bid/ask price, bid/ask
                          nghĩa kinh tế/tài chính   volume, symbol, market
                                                    phase; nhiều hơn 3
                                                    trường

  Dữ liệu theo thời gian  Nếu đưa nhận định theo    Thu thập nội ngày; mục
                          thời gian: tự thu         tiêu tối thiểu 5 phiên
                          thập/lưu đủ để kiểm       giao dịch nếu
                          chứng; khuyến nghị tối    lịch/quyền truy cập cho
                          thiểu 05 phiên, ưu tiên   phép
                          10+ nếu có thể            

  Múi giờ                 `Asia/Ho_Chi_Minh`        Lưu UTC cho kỹ thuật và
                          (UTC+7), nhất quán        lưu/hiển thị VN
                                                    timezone đúng IANA

  Chất lượng dữ liệu      Xử lý missing, duplicate, W3 validation/quality
                          sai kiểu, mất kết nối, dữ flags; W6 tests
                          liệu muộn, message bất    
                          thường                    

  Rate limit              Không vượt 5              W2 rate limiter, ưu
                          requests/second/client;   tiên WS `stockInfo`
                          ưu tiên WS thay REST      
                          polling dày               

  Tái lập                 Truy vết nguồn, biến đổi, Raw event → canonical
                          quy trình tạo kết quả     quote → finance output
                                                    → quote_id
  -------------------------------------------------------------------------

## 5. Yêu cầu giao diện tối thiểu

Giao diện phải có đủ: 1. Tên sản phẩm, mục tiêu và người dùng. 2. Thời
điểm dữ liệu cập nhật gần nhất và trạng thái kết nối. 3. Ít nhất 03 chỉ
số/kết quả tổng hợp có ý nghĩa. 4. Ít nhất 02 dạng trực quan hóa phù
hợp. 5. Bộ lọc/chọn mã/chỉ số/khoảng thời gian phù hợp. 6. Khu vực phân
tích/cảnh báo/xếp hạng/giải thích --- thể hiện giá trị tài chính. 7. Mô
tả ngắn phương pháp tính và giới hạn. 8. Xử lý rõ no-data, disconnect,
API error; không treo hoặc gây hiểu nhầm.

**Ánh xạ cho LiquidityGuard:** - 3 KPI: spread, depth, OBI; có thể bổ
sung coverage/VWAP. - 2 trực quan: order-book ladder ba mức và
cumulative fill/simulation chart. Time-series là trực quan bổ sung khi
dữ liệu đủ. - Bộ lọc: mã cổ phiếu, BUY/SELL, khối lượng, LIVE/REPLAY,
khoảng thời gian replay. - Trạng thái: LIVE / REPLAY / SYNTHETIC_TEST,
last update, connection health, stale.

## 6. Yêu cầu kiến trúc và mã nguồn

Đề đưa ra chuỗi kiến trúc tối thiểu:
`NEO API → Thu thập dữ liệu → Chuẩn hóa/Lưu trữ → Logic tài chính → Phân tích/Mô hình → Giao diện → Người dùng`.

Yêu cầu mã nguồn: - Không chứa credential thật; có `.env.example`. -
Tách tương đối lớp API, data, finance và UI. - Có log/thông báo lỗi đủ
xác định nguyên nhân khi mất kết nối/API lỗi. - Có kiểm thử tự động hoặc
có thể tái hiện cho các hàm tính toán quan trọng. - README phải hướng
dẫn cài đặt, cấu hình, chạy, cấu trúc dữ liệu và giới hạn.

## 7. An toàn --- điều kiện bắt buộc, không phải tính năng tùy chọn

-   Đề mặc định chỉ dùng dữ liệu/chức năng không phát sinh giao dịch
    tiền thật.
-   Không tự động gửi lệnh mua/bán/sửa/hủy thật nếu chưa có chấp thuận
    riêng bằng văn bản của giảng viên.
-   Đề lưu ý thông báo VPBankS ngày 12/10/2026: NEO API chưa có môi
    trường thử nghiệm riêng cho khách hàng và lệnh đặt qua API là lệnh
    thật. Dù tài liệu kỹ thuật có thể liệt kê URL UAT, **không mặc định
    sinh viên có quyền dùng UAT**.
-   Không tổ chức giao dịch phối hợp giữa sinh viên; không tạo khối
    lượng/cung cầu hoặc ảnh hưởng giá; không dùng lợi nhuận tiền thật
    làm tiêu chí.
-   Không dùng thông tin đăng nhập của người khác, không công bố dữ liệu
    tài khoản cá nhân.
-   Nếu có nội dung hỗ trợ quyết định đầu tư, phải ghi rõ đây là công cụ
    phân tích học thuật, không phải khuyến nghị đầu tư.

**Hệ quả cho LiquidityGuard:** chỉ implement read-only market data.
Không gọi order API, không test bằng cách gửi lệnh thật, không dựa vào
việc có UAT để cho phép giao dịch.

## 8. Rubric chính thức --- 100 điểm

  ------------------------------------------------------------------------
  \#               Tiêu chí                          Điểm Bằng chứng W1
                                                          cần kiểm soát
  ---------------- ---------------- --------------------- ----------------
  1                Vấn đề và giá                       15 Problem
                   trị Công nghệ                          statement,
                   tài chính                              persona, nhu
                                                          cầu, giá trị

  2                Khai thác NEO                       20 API mapping,
                   API và kỹ thuật                        WS/raw storage,
                   dữ liệu                                canonical
                                                          schema, quality,
                                                          rate limit,
                                                          lineage

  3                Phương pháp tài                     20 Công thức, giả
                   chính và chiều                         định, lý do chọn
                   sâu phân tích                          biến, kiểm thử,
                                                          diễn giải có
                                                          trách nhiệm

  4                Chất lượng triển                    20 Module hóa, xử
                   khai kỹ thuật                          lý lỗi, config
                                                          an toàn, tests,
                                                          tái chạy

  5                Chất lượng sản                      10 Dashboard,
                   phẩm và trải                           filter, KPI,
                   nghiệm sử dụng                         visuals,
                                                          freshness,
                                                          lỗi/no-data

  6                Kiểm thử và kiểm                    10 Test plan, tính
                   chứng                                  tay, đối chiếu
                                                          dữ liệu, lỗi/kết
                                                          nối, hạn chế

  7                Tài liệu, báo                        5 README, report,
                   cáo và trình bày                       source
                                                          citations,
                                                          demo/video, hiểu
                                                          biết khi bảo vệ

                   **Tổng**                       **100** 
  ------------------------------------------------------------------------

### Các giới hạn điểm quan trọng

-   Không có sản phẩm chạy được hoặc không có bằng chứng trình diễn:
    toàn bài không vượt 60/100.
-   NEO API không phải thành phần cốt lõi: toàn bài không vượt 50/100.
-   Chỉ hiển thị dữ liệu, không có logic tài chính: không đạt mức tối đa
    ở tiêu chí 3 và 5.
-   Lộ credential thật: phải thu hồi/đổi credential ngay và bị trừ
    nghiêm trọng ở tiêu chí kỹ thuật.
-   Tự ý phát sinh giao dịch thật: không tuân thủ yêu cầu an toàn và
    phải được giảng viên xử lý.

## 9. Sản phẩm phải nộp

1.  Mã nguồn đầy đủ, không có khóa bí mật, có hướng dẫn chạy.
2.  Sản phẩm chạy được.
3.  Báo cáo cuối kỳ: khuyến nghị 8--12 trang A4, không tính phụ lục.
4.  Video demo hoặc đường dẫn video.

Tên file theo đề: - `MSSV_HoTen_NEOAPI_FinTech.zip` -
`MSSV_HoTen_BaoCao.pdf` hoặc `.docx` - `MSSV_HoTen_Demo.mp4` hoặc đường
dẫn video.

## 10. Khung báo cáo cuối kỳ

1.  Tóm tắt điều hành.
2.  Vấn đề và nhu cầu người dùng.
3.  Thiết kế sản phẩm.
4.  Dữ liệu NEO API.
5.  Phương pháp tài chính/phân tích.
6.  Triển khai sản phẩm.
7.  Kiểm thử và kết quả.
8.  Hạn chế và sử dụng có trách nhiệm.
9.  Hướng phát triển.
10. Kết luận. Phụ lục: từ điển dữ liệu, công thức, kết quả test, hướng
    dẫn cài đặt, mã nguồn/video nếu cần.

## 11. Liêm chính học thuật và AI

Được sử dụng tài liệu, thư viện và AI hỗ trợ nếu học phần không có quy
định riêng, nhưng sinh viên chịu trách nhiệm hoàn toàn về mã nguồn/kết
quả/trích dẫn: - Phải hiểu và giải thích được code, công thức, quyết
định thiết kế. - Không nộp code/văn bản của người khác như sản phẩm của
mình. - Ghi nguồn cho code/tài liệu ngoài có ảnh hưởng đáng kể. - Không
dùng dữ liệu giả để tạo kết quả đẹp mà không ghi rõ là mô phỏng. - Nếu
dùng AI sinh giải thích thị trường, phải giảm nguy cơ phát biểu sai và
không trình bày nội dung AI như sự thật đã kiểm chứng.

## 12. Lưu ý về loại đồ án

Đề ghi rõ đây là **đồ án cá nhân**. Các W1--W7 chỉ là cách phân chia vai
trò kỹ thuật để quản lý công việc; không biến đồ án thành bài nhóm và
không tổ chức giao dịch phối hợp giữa sinh viên.
