# W1.01 --- PROBLEM STATEMENT

**Tên sản phẩm:** LiquidityGuard\
**Phiên bản:** 1.0 --- Working Draft\
**Ngày:** 07/11/2026\
**Trạng thái:** DESIGNED; chưa xác nhận bằng nghiên cứu người dùng thực
tế.

## 1. Tóm tắt sản phẩm

LiquidityGuard là công cụ hỗ trợ ra quyết định theo hướng
**read-only** dành cho nhà đầu tư cá nhân giao dịch cổ phiếu cơ sở. Công
cụ sử dụng dữ liệu giá và khối lượng mua/bán ba mức từ SSI FastConnect để mô tả
độ sâu đang hiển thị và mô phỏng một lệnh mua/bán giả định quét qua tối
đa ba mức giá.

Sản phẩm trả lời câu hỏi: "Nếu tôi muốn mua hoặc bán Q cổ phiếu ngay tại
thời điểm quan sát, ba mức giá đang hiển thị có thể đáp ứng bao nhiêu
khối lượng, VWAP ước tính của phần được đáp ứng là bao nhiêu và còn dư
bao nhiêu?"

Sản phẩm **không** đặt lệnh, không dự báo giá, không đảm bảo khớp lệnh
và không đại diện toàn bộ thanh khoản ẩn hoặc thanh khoản sẽ xuất hiện
sau thời điểm quan sát.

## 2. Persona mục tiêu

**Persona chính --- Nhà đầu tư cá nhân chủ động theo dõi cổ phiếu cơ
sở**

-   Có tài khoản SSI và có thể đăng ký API Key FastConnect Market Data.
-   Theo dõi một hoặc một số mã cổ phiếu cơ sở.
-   Trước khi tự quyết định đặt lệnh, muốn xem nhanh spread, khối lượng
    chờ mua/bán ba mức và tác động ước tính của khối lượng dự kiến.
-   Có thể hiểu các khái niệm cơ bản như giá mua, giá bán, khối lượng,
    spread; không nhất thiết biết lập trình.
-   Cần nhìn thấy thời điểm dữ liệu, trạng thái kết nối và cảnh báo khi
    dữ liệu không đủ tin cậy.

**Lưu ý:** Đây là persona giả định để thiết kế MVP, chưa phải kết quả
khảo sát. Không viết trong báo cáo rằng đã phỏng vấn người dùng nếu chưa
thực hiện.

## 3. Vấn đề cần giải quyết

Khi nhà đầu tư muốn mua/bán một khối lượng lớn hơn lượng đang chờ tại
mức giá tốt nhất, chỉ nhìn giá mua tốt nhất/giá bán tốt nhất có thể
không đủ để hình dung: - Khối lượng dự kiến có thể được đáp ứng trong ba
mức giá đang hiển thị hay không. - Phần khối lượng nào sẽ phải đi qua
mức giá tiếp theo. - Giá bình quân ước tính của phần khối lượng được đáp
ứng. - Phần khối lượng còn thiếu ngoài ba mức quan sát. - Dữ liệu đang
xem có mới, đầy đủ và thuộc phiên giao dịch được phép mô phỏng hay
không.

Đây là vấn đề thiết kế sản phẩm cần kiểm chứng. Không khẳng định mọi nhà
đầu tư đều gặp vấn đề này hoặc mức độ thiệt hại cụ thể nếu chưa có khảo
sát/bằng chứng.

## 4. Nhu cầu / Job to be done

"Khi chuẩn bị tự quyết định mua hoặc bán một mã cổ phiếu với khối lượng
Q, tôi muốn xem độ sâu bid/ask ba mức và mô phỏng lượng có thể được đáp
ứng ở từng mức, để hiểu mức giá bình quân ước tính và phần còn thiếu
trước khi tự đưa ra quyết định."

## 5. Giải pháp đề xuất

Luồng người dùng: 1. Chọn mã cổ phiếu từ SSI Market Data. 2. Xem dữ
liệu bid/ask ba mức, trạng thái thị trường, thời điểm nhận dữ liệu và
trạng thái LIVE/REPLAY. 3. Xem các chỉ báo: spread, depth mua/bán, OBI.
4. Nhập chiều BUY/SELL và khối lượng giả định. 5. Nhận kết quả mô phỏng
theo từng mức giá: khối lượng được đáp ứng, khối lượng chưa đáp ứng,
coverage, VWAP của phần được đáp ứng và slippage ước tính so với giá tốt
nhất cùng chiều. 6. Nếu dữ liệu stale, thiếu mức, sai định dạng, ngoài
phiên được phép hoặc chưa xác định được snapshot đầy đủ, hệ thống từ
chối mô phỏng và nêu lý do. 7. Có thể chuyển sang REPLAY để xem lại dữ
liệu đã lưu.

## 6. Giá trị mang lại

-   Chuyển bảng bid/ask thành một phép mô phỏng định lượng dễ hiểu.
-   Cho người dùng thấy giới hạn của độ sâu ba mức thay vì giả định toàn
    bộ khối lượng sẽ được đáp ứng.
-   Tăng tính minh bạch nhờ hiển thị nguồn, thời điểm và cờ chất lượng
    dữ liệu.
-   Tạo một sản phẩm có logic tài chính kiểm chứng được, thay vì chỉ là
    dashboard hiển thị giá.

## 7. Chỉ số thành công của MVP

Các mục tiêu dưới đây là **target thiết kế**, không phải kết quả đã
đạt: - Người dùng chọn được một mã và xem được snapshot hợp lệ. -
Dashboard hiển thị tối thiểu ba KPI: spread, depth, OBI. - Người dùng mô
phỏng được cả BUY và SELL. - Khi khối lượng yêu cầu vượt tổng depth ba
mức, hệ thống chỉ ghi nhận phần được đáp ứng trong ba mức và báo phần
chưa đáp ứng. - Có thể replay một khoảng dữ liệu đã lưu mà không cần kết
nối live. - Dữ liệu không hợp lệ/stale không được âm thầm dùng cho mô
phỏng. - Không phát sinh lệnh giao dịch thật.

## 8. Giới hạn và tuyên bố bắt buộc

LiquidityGuard là công cụ mô phỏng dựa trên **ảnh chụp độ sâu hiển
thị tối đa ba mức**. Kết quả không phải: - Xác nhận lệnh có thể khớp
thực tế. - Cam kết giá khớp, khối lượng khớp hoặc thời gian khớp. - Mô
hình đầy đủ của order matching engine. - Dự báo biến động giá. - Khuyến
nghị mua/bán. - Tổng chi phí giao dịch sau phí, thuế và các chi phí
khác.

Kết quả không tính vị trí hàng đợi, lệnh ẩn, thay đổi sổ lệnh trong lúc
người dùng ra quyết định, độ trễ truyền dữ liệu, hủy/sửa lệnh của người
khác hoặc thanh khoản ngoài ba mức.

## 9. Yêu cầu đề thi phải giữ đúng

-   SSI FastConnect là nguồn duy nhất; MVP dùng Quote Streaming có lưu
    dữ liệu và Market Data REST liên quan theo quyết định Phương án A.
-   Có ít nhất ba trường dữ liệu có ý nghĩa tài chính; sản phẩm thực tế
    dùng sáu mức giá/khối lượng bid/ask cùng symbol và market phase.
-   Vì sản phẩm có LIVE/REPLAY và nhận định theo thời gian, mục tiêu thu
    thập tối thiểu 05 phiên giao dịch; đề khuyến nghị 10 phiên trở lên
    nếu thời gian cho phép.
-   Mọi timestamp phải lưu/trình bày nhất quán theo `Asia/Ho_Chi_Minh`
    (UTC+7); có thể lưu thêm UTC để xử lý kỹ thuật.
-   Không giao dịch thật; đây là công cụ phân tích học thuật, không phải
    khuyến nghị đầu tư.

## 10. Giả định cần xác minh

  -----------------------------------------------------------------------
  ID                Giả định          Cách xác minh     Owner
  ----------------- ----------------- ----------------- -----------------
  A01               Tài khoản được    W2 đăng nhập      W2
                    cấp API Key SSI  Production và 
                                      lưu status đã che 
                                      bí mật            

  A02               Có thể subscribe  W2 lưu message    W2
                    Quote Streaming  WebSocket thật    
                    mã cơ sở                            

  A03               Giá và khối lượng Đối chiếu docs,   W2/W3
                    có đơn vị xác     bảng giá và xác   
                    định              nhận SSI          

  A04               Message WS có đủ  Thu thập chuỗi    W2/W3
                    dữ liệu để tạo    message và xác    
                    snapshot ba mức   minh semantics    

  A05               Có thể xác định   SSI WebSocket     W2/W3
                    market phase      `market.flag` và  
                                      kiểm tra join     
                                      theo thời gian    

  A06               Dữ liệu đủ tần    Đo thời gian nhận W2/W3
                    suất cho          và tỷ lệ mất      
                    live/replay       message           
  -----------------------------------------------------------------------

## 11. Câu mô tả ngắn dùng trong báo cáo

"LiquidityGuard là công cụ hỗ trợ nhà đầu tư cá nhân đánh giá độ sâu
sổ lệnh ba mức và mô phỏng tác động của một khối lượng mua/bán giả định
trên phần thanh khoản đang hiển thị, thông qua dữ liệu SSI FastConnect. Hệ thống
cung cấp spread, depth, OBI, coverage, VWAP và slippage ước tính; đồng
thời kiểm soát độ mới và chất lượng dữ liệu. Sản phẩm chỉ hỗ trợ phân
tích, không thực hiện giao dịch thật và không cam kết khả năng khớp
lệnh."
