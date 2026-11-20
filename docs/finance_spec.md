# W1.06 --- FINANCE SPEC / CÔNG THỨC VÀ MÔ PHỎNG

**Phiên bản:** 1.0 --- Working Draft\
**Ngày:** 07/11/2026\
**Mục tiêu:** Đặc tả công thức đủ rõ để W4 lập trình độc lập và W6 kiểm
thử bằng phép tính tay.

## 1. Phạm vi và nguyên tắc

LiquidityGuard phân tích **ba mức giá mua và ba mức giá bán đang hiển
thị**. Mọi kết quả là ước tính trên snapshot đã lưu/nhận, không phải kết
quả khớp lệnh thực tế.

-   Bid1 là mức mua tốt nhất (giá bid cao nhất trong ba mức).
-   Ask1 là mức bán tốt nhất (giá ask thấp nhất trong ba mức).
-   Khi mô phỏng BUY, lệnh giả định tiêu thụ ask1 → ask2 → ask3.
-   Khi mô phỏng SELL, lệnh giả định tiêu thụ bid1 → bid2 → bid3.
-   Không mô phỏng vượt mức 3.
-   Không tính phí, thuế, vị trí queue, lệnh ẩn hoặc thay đổi sổ lệnh
    trong tương lai.

## 2. Điều kiện dữ liệu đầu vào

Không tính KPI/mô phỏng nếu: - Snapshot không hoàn chỉnh hoặc semantics
partial/full chưa xác minh. - Giá cần dùng không parse được thành số. -
Khối lượng bị thiếu/âm/sai kiểu. - Unit chưa được xác minh. - Quote
stale. - Market phase không nằm trong allow-list đã được xác nhận. - Sổ
lệnh có dấu hiệu sai thứ tự hoặc ask1 \<= bid1 mà chưa được xử lý. - Dữ
liệu là SYNTHETIC_TEST nhưng giao diện đang ở chế độ LIVE.

Ngưỡng stale đề xuất ban đầu: 5 giây. Đây là tham số thiết kế, cần hiệu
chỉnh sau khi đo tần suất message thực tế; không phải cam kết của
SSI FastConnect.

## 3. Spread

### 3.1. Spread tuyệt đối

`spread_abs = ask_price_1 - bid_price_1`

Đơn vị cùng đơn vị giá nguồn. Nếu price unit được xác minh là VND/CP thì
kết quả là VND/CP.

### 3.2. Mid-price

`mid_price = (ask_price_1 + bid_price_1) / 2`

### 3.3. Spread tương đối

`spread_pct = (spread_abs / mid_price) * 100`

### 3.4. Spread basis points

`spread_bps = (spread_abs / mid_price) * 10,000`

Nếu thiếu một trong hai best price hoặc mid_price \<= 0 thì trả `null`
và ghi lý do; không trả 0.

## 4. Depth ba mức

### 4.1. Bid depth

`bid_depth_3 = bid_qty_1 + bid_qty_2 + bid_qty_3`

### 4.2. Ask depth

`ask_depth_3 = ask_qty_1 + ask_qty_2 + ask_qty_3`

Đơn vị theo `quantity_unit` đã xác minh (dự kiến cổ phiếu). Không cộng
giá vào depth khối lượng.

### 4.3. Notional depth --- tùy chọn

`bid_notional_3 = Σ(bid_price_i * bid_qty_i)`
`ask_notional_3 = Σ(ask_price_i * ask_qty_i)`

Chỉ hiển thị notional khi price unit và quantity unit đã xác minh. Không
bắt buộc để MVP đạt ba KPI.

## 5. Order Book Imbalance (OBI)

OBI trong MVP dùng **khối lượng cổ phiếu** ba mức, không phải giá trị
tiền:

`OBI = (bid_depth_3 - ask_depth_3) / (bid_depth_3 + ask_depth_3)`

Miền giá trị: \[-1, +1\]. - OBI \> 0: khối lượng bid hiển thị lớn hơn
ask hiển thị. - OBI \< 0: khối lượng ask hiển thị lớn hơn bid hiển
thị. - OBI gần 0: khối lượng hai phía tương đối cân bằng.

Nếu tổng depth bằng 0 hoặc dữ liệu thiếu/không hợp lệ, OBI = null. OBI
không được diễn giải là xác suất tăng/giảm giá hay khuyến nghị mua/bán.

## 6. Mô phỏng BUY

Input: - `side = BUY` - `requested_qty = Q`, integer dương. - Ask levels
đã được sắp xếp tăng dần theo giá: ask1, ask2, ask3.

Thuật toán: 1. `remaining = Q`, `filled = 0`, `notional = 0`. 2. Với
từng mức ask i từ 1 đến 3: - `take_i = min(remaining, ask_qty_i)` -
`filled_i = take_i` - `notional += take_i * ask_price_i` -
`remaining -= take_i` 3. Dừng khi remaining = 0 hoặc đã hết mức 3. 4.
`unfilled_qty = remaining` 5. `coverage = filled / Q` 6. Nếu filled \>
0: `VWAP = notional / filled`; nếu filled = 0: VWAP = null.

## 7. Mô phỏng SELL

Input: - `side = SELL` - `requested_qty = Q`, integer dương. - Bid
levels đã được sắp xếp giảm dần theo giá: bid1, bid2, bid3.

Lặp tương tự BUY nhưng đi theo bid1 → bid2 → bid3.

## 8. Slippage ước tính

Slippage chỉ đo chênh lệch giữa VWAP của phần được đáp ứng và giá tốt
nhất cùng phía.

BUY: - `buy_slippage_abs = VWAP - ask_price_1` -
`buy_slippage_bps = (buy_slippage_abs / ask_price_1) * 10,000`

SELL: - `sell_slippage_abs = bid_price_1 - VWAP` -
`sell_slippage_bps = (sell_slippage_abs / bid_price_1) * 10,000`

Nếu không có khối lượng được đáp ứng hoặc best price \<= 0 thì slippage
= null. Nếu slippage âm trong điều kiện book hợp lệ, gắn cảnh báo để
kiểm tra dữ liệu/thứ tự giá; không âm thầm lấy trị tuyệt đối.

## 9. Quy tắc partial fill

Nếu Q lớn hơn tổng depth ba mức: - Chỉ tính khối lượng có thể lấy từ ba
mức. - `unfilled_qty > 0`. - `coverage < 1`. - VWAP tính trên phần
`filled_qty`, không chia cho requested_qty. - Không giả định phần còn
lại được khớp ở mức giá thứ tư hoặc mức giá bất kỳ. - Giao diện phải
hiển thị "Ngoài độ sâu ba mức quan sát được" thay vì đưa ra giá giả
định.

Kiểm thử biên bắt buộc: nếu BUY `400` cổ phiếu nhưng tổng ask depth quan
sát được ở ba mức chỉ là `350`, kết quả phải là `filled_qty=350`,
`unfilled_qty=50`, `coverage=0.875` (87,5%). Không được tạo level 4 hoặc
gán giá cho 50 cổ phiếu chưa được đáp ứng.

## 10. Ví dụ tính tay --- dữ liệu SYNTHETIC_TEST

**Giả định unit trong ví dụ:** giá là VND/CP, khối lượng là cổ phiếu.
Đây là unit giả định cho fixture để kiểm thử công thức; W2/W3 vẫn phải
xác minh unit từ SSI thực tế.

  Phía     Mức      Giá   Khối lượng
  ------ ----- -------- ------------
  Bid        1   29,750      100,000
  Bid        2   29,700       80,000
  Bid        3   29,650       50,000
  Ask        1   29,800       60,000
  Ask        2   29,850      100,000
  Ask        3   29,900      120,000

### Ví dụ 1 --- KPI

-   Spread tuyệt đối = 29,800 − 29,750 = **50**.
-   Mid-price = (29,800 + 29,750) / 2 = **29,775**.
-   Spread % = 50 / 29,775 × 100 = **0.167926%**.
-   Spread bps = 50 / 29,775 × 10,000 = **16.7926 bps**.
-   Bid depth = 100,000 + 80,000 + 50,000 = **230,000 shares**.
-   Ask depth = 60,000 + 100,000 + 120,000 = **280,000 shares**.
-   OBI = (230,000 − 280,000) / (230,000 + 280,000) = **−0.098039**.

### Ví dụ 2 --- BUY 100,000 shares

-   Ask1: lấy 60,000 × 29,800 = 1,788,000,000.
-   Ask2: lấy 40,000 × 29,850 = 1,194,000,000.
-   Ask3: không cần lấy.
-   Filled = 100,000; unfilled = 0; coverage = 100%.
-   Notional = 2,982,000,000.
-   VWAP = 2,982,000,000 / 100,000 = **29,820**.
-   Slippage = 29,820 − 29,800 = **20**.
-   Slippage bps = 20 / 29,800 × 10,000 = **6.7114 bps**.

### Ví dụ 3 --- BUY 400,000 shares vượt depth

-   Ask1 lấy 60,000.
-   Ask2 lấy 100,000.
-   Ask3 lấy 120,000.
-   Tổng filled = **280,000**.
-   Unfilled = 400,000 − 280,000 = **120,000**.
-   Coverage = 280,000 / 400,000 = **70%**.
-   Notional = 60,000×29,800 + 100,000×29,850 + 120,000×29,900 =
    **8,361,000,000**.
-   VWAP phần được đáp ứng = 8,361,000,000 / 280,000 = **29,860.7143**.
-   Slippage = 29,860.7143 − 29,800 = **60.7143**.
-   Không được báo rằng 400,000 cổ phiếu đã được mua hoặc 120,000 còn
    lại sẽ khớp ở giá nào.

### Ví dụ 4 --- SELL 150,000 shares

-   Bid1 lấy 100,000 × 29,750 = 2,975,000,000.
-   Bid2 lấy 50,000 × 29,700 = 1,485,000,000.
-   Filled = 150,000; unfilled = 0; coverage = 100%.
-   Notional = 4,460,000,000.
-   VWAP = 4,460,000,000 / 150,000 = **29,733.3333**.
-   Slippage = 29,750 − 29,733.3333 = **16.6667**.

## 11. Output contract cho W5

Mỗi lần mô phỏng W4 trả tối thiểu: - `side` - `requested_qty` -
`filled_qty` - `unfilled_qty` - `coverage_ratio` - `vwap_filled` -
`best_price` - `slippage_abs` - `slippage_bps` - `level_fills`: danh
sách mức giá và khối lượng lấy ở từng mức - `is_simulatable` -
`rejection_reason` hoặc `warnings` - `source_mode`:
LIVE/REPLAY/SYNTHETIC_TEST - `quote_id`

## 12. Hai ví dụ từ chối mô phỏng

1.  `askPrice1 = "ATO"` hoặc `"ATC"`: không parse thành số; không mô
    phỏng phía BUY nếu best ask cần dùng không hợp lệ.
2.  Quote nhận cách đây 15 giây trong khi ngưỡng stale đang cấu hình 5
    giây: hiển thị stale, khóa mô phỏng LIVE; vẫn cho replay record cũ
    nếu người dùng chọn REPLAY.

## 13. Những gì công thức không thể kết luận

-   Không dự đoán giá sau khi lệnh đi vào thị trường.
-   Không biết các lệnh khác có bị hủy/sửa trước khi lệnh giả định tới
    sổ hay không.
-   Không biết queue position.
-   Không biết hidden liquidity.
-   Không biết mức giá thứ tư trở đi.
-   Không bao gồm phí/thuế.
-   Không phải backtest hiệu quả đầu tư.
