# LIQUIDITYGUARD — EXECUTION LAB (MASCOT) — CODEX IMPLEMENTATION SPEC V1.0

> **MỤC TIÊU:** Hiện thực hóa trang **Mô phỏng lệnh / Execution Lab** của dự án Neo-LiquidityGuard hiện hữu, bám sát ảnh `REFERENCE_EXECUTION_LAB_MASCOT.png` đến mức tối đa về bố cục, màu sắc, typography, bo góc và thành phần. Đây phải là ứng dụng Streamlit/Plotly hoạt động thực tế, không phải ảnh nền, HTML không tương tác, hay một app được viết lại từ đầu. **Ảnh tham chiếu chứa số minh họa, không phải kết quả SSI hợp lệ.**

## 0. Luật ưu tiên — KHÔNG THƯƠNG LƯỢNG

1. **Ảnh reference quyết định giao diện; mã nguồn/contract dữ liệu hiện có quyết định cách chạy; công thức tài chính đúng quyết định nội dung số.** Khi ảnh có kết quả sai nghiệp vụ, sửa số/nhãn chứ không sao chép lỗi.
2. Chỉ triển khai/sửa trang **Mô phỏng lệnh (Execution Lab)** và các component dùng chung cần thiết; không tự tiện tái thiết kế toàn bộ 7 trang. Sidebar, header và shared palette có thể được đồng bộ trên các trang theo kiến trúc hiện tại.
3. KHÔNG chuyển từ Streamlit sang React/Next.js; sử dụng Python + Streamlit + Plotly + CSS scoped trong repo trừ khi dự án thực tế đã đổi framework (phải báo trước khi làm).
4. KHÔNG sửa hoặc vô hiệu hóa W2 SSI Collector, W3 raw/replay/quality, W4 toán tài chính chỉ để làm UI chạy. Không thay `market_phase` thành LO dựa trên đồng hồ. Không dùng dữ liệu synthetic để lấp các lỗ hổng LIVE. Không tự công bố LIVE khi collector offline hoặc timestamp stale.
5. Không có **đặt lệnh thật**, đặt giá mua/bán thực tế, tư vấn nên mua/bán; đây là mô phỏng định lượng trong **3 mức Bid/Ask đầu tiên**. Không giả định một lệnh ảo đã khớp.
6. Số liệu trong ảnh như `FPT 142.800`, `VWAP 100.000`, `4.930/5.000`, `98,6%`, `7,4 bps`, các ví dụ `09/11/2024` chỉ là placeholder; **không hardcode** và không trộn các nguồn REST, REPLAY, LIVE và SYNTHETIC_TEST. Không hiển thị avatar/tên người thật được tự bịa.
7. 70 CP chưa đáp ứng **KHÔNG được gắn nhãn L4** như thể nhìn thấy mức 4. Chỉ ghi `Chưa đáp ứng trong L1–L3: 70 CP`; không dự đoán giá khớp ở L4.
8. Việc hiển thị Data Trust/flag **phải khớp với từng snapshot**; `w4_live_gate=OPEN` toàn cục không bảo đảm mã/snapshot đang chọn đủ điều kiện.
9. Trước khi sửa, đọc `README.md`, `pyproject.toml`, `src/app/dashboard.py`, `src/app/pages.py`, `src/app/components.py`, `src/app/charts.py`, `src/app/styles.py`, `src/app/state.py`, `src/app/view_models.py`, `src/finance/execution.py`, `src/finance/liquidity.py`, `src/finance/eligibility.py`, `src/data/replay.py`, `src/data/quote_store.py`, các test; chỉ dùng đường dẫn thực sự tồn tại ở repo hiện tại. Có thể dựa vào `src/app/assets/mascot.png` nếu có. KHÔNG mở/in `.env` hoặc API key.
10. Tạo backup/commit điểm an toàn trước khi đổi UI. Xuất ảnh screenshot giao diện thật ở viewport chuẩn và đối chiếu với reference; báo cáo những khác biệt chưa đạt.

## 1. Ảnh chuẩn & mục tiêu kích thước

- Ảnh chuẩn: `REFERENCE_EXECUTION_LAB_MASCOT.png` độ phân giải **1672 × 941 px**.
- Desktop priority: viewport 1672×941 hoặc tỷ lệ ~16:9. Tổng diện tích full width; **sidebar** trái x=0–228 (~228px); **header toàn cục** ở vùng phải sidebar y=0–66 (~66px); vùng content trung tâm x=244–1230 (~986px); **right rail** x=1245–1660 (~415px). Khoảng cách giữa các card 12–16px; mép 14–16px.
- Không tạo khu trống lớn, không đẩy 5 biểu đồ xuống một cột ở màn 1440–1672px. Nội dung chính chiếm ~70–74% vùng trừ sidebar, cột phải ~27–30% vùng trừ sidebar.
- Khu giữa (tính từ y≈80) theo thứ tự **Hero → Control Strip → KPI Result Strip → Explain Strip → Chart 3 cột → Chart 2 cột → Formula Expander**. Không đảo thứ tự.
- Sidebar + header + right rail dính (sticky/consistent) hợp lý; riêng chart có scroll khi màn hình thấp, không thu nhỏ chữ xuống dưới 11px.

### 1.1. Bảng hình học desktop (mốc x,y có thể lệch ±8–12 px tùy renderer)

| Thành phần | Toạ độ tương đối trong ảnh | Chiều cao mục tiêu | Ghi chú |
|---|---|---:|---|
| Sidebar | x 0–228, y 0–940 | toàn màn | tím mận, menu dọc |
| Top bar | x 242–1660, y 0–67 | 62–68px | mode, search, date, session, bell, profile |
| Hero | center x 244–1230, y 80–254 | 172–180px | 3D mascot ở phải, text trái |
| Simulation inputs | center y 264–325 | 58–65px | BUY/SELL, mã, khối lượng, CTA |
| KPI results | center y 334–402 | 60–70px | VWAP, filled/unfilled, impact, coverage |
| Natural-language insight | center y 409–496 | 80–90px | diễn giải 1–2 câu + 2–3 tín hiệu |
| Chart row 1 | center y 505–679 | ~175px | 3 card ngang |
| Chart row 2 | center y 687–839 | ~150px | 2 card ngang |
| Formula expander | center y 846–914 | ~65px | nhãn + mô tả, mở chi tiết |
| Watchlist | right x1245–1660, y 80–367 | ~285px | ~5 mã, có nguồn giá |
| Session Snapshot | right y 379–606 | ~225px | time span, spread/OBI, valid count |
| Data Trust | right y 618–780 | ~160px | status/flags/bằng chứng |

## 2. DESIGN TOKENS — CHỐT MÀU

```css
:root {
  --lg-deep-plum: #3E2F4F;     /* sidebar, nền đậm */
  --lg-text: #30243C;          /* nội dung trên nền trắng */
  --lg-dusty-lavender: #BDAFD1;
  --lg-soft-lilac: #DCCFF0;
  --lg-warm-sand: #D7B38C;
  --lg-cream: #F2E6D7;
  --lg-blush: #F3C9DD;
  --lg-primary: #9563C4;
  --lg-mint: #A8DDB5;
  --lg-coral: #F2A0B6;
  --lg-peach: #F4BF91;
  --lg-paper: #FAF7FC;
  --lg-border: rgba(62,47,79,.12);
  --lg-shadow: 0 12px 30px rgba(48,36,60,.11);
  --lg-card-radius: 23px;
  --lg-control-radius: 15px;
  --lg-pill-radius: 999px;
}
```

- **Nền nội dung:** gradient rất nhạt `#FCF9FF → #F2EAF7`; không làm tối cả nền content.
- **Sidebar:** `#3E2F4F` hoặc gradient tới `#5C4368`; active menu nền `#DCCFF0`/tím sáng, text #30243C. Icon outline khoảng 20px.
- **Hero:** gradient từ `#80698E` qua `#A986BE` đến `#BDAFD1`, card radius 25–27px; chữ trắng; mascot tạo tương phản.
- **Control strip:** nền trắng hồng nhạt `#FCF4FB`; CTA gradient tím #9563C4 → #8753B3.
- **Result strip:** `#FEF9FE` nhẹ, borders/subtle separators; số màu text Plum; coverage xanh mint nếu đủ điều kiện.
- **Insight:** blush/cream gradient nhẹ; warning soft coral khi thiếu độ sâu hoặc không có dữ liệu.
- **Charts:** card nền trắng/cream `#FFF9FA`; Bid tím `#9563C4`, Ask peach `#F4BF91`; OBI >0 tím hoặc mint; <0 coral/hồng; gridline rgba(62,47,79,0.09).
- **Watchlist/Trust:** white pastel; positive/negative trạng thái dùng color + icon + text, không chỉ dựa vào màu.
- **Typography:** `Nunito Sans`/`Manrope` (nếu sẵn, fallback `Inter`, `Arial`, sans-serif, font hỗ trợ tiếng Việt). Hero title ~42px desktop, H2 ~20px, card title 16–19px bold, body 13–14px, chart labels >=11–12px. KPI 21–27px, dùng tabular nums. Không font trang trí khó đọc.
- **Radii:** 22–26px cards, input/button 12–16px, pill full; shadow mềm, không viền neon. CSS scoped `.lg-*`, không phụ thuộc class hashed của Streamlit.

## 3. Component-by-component — chính xác thứ tự

### A. Sidebar (trái, rộng 228 px)
- Logo: icon đầu gấu mèo nhỏ (có thể lấy từ asset riêng) + `LiquidityGuard` trắng; subtitle `Liquidity Intelligence for Smarter Execution` nhỏ.
- Menu theo đúng thứ tự: **Tổng quan; Mô phỏng lệnh (active); Replay phiên; So sánh mã; Data Trust; Cảnh báo; Cài đặt**.
- Các mục có icon đồng nhất stroke, full card active màu lilac với border radius 22px; click điều hướng thật, giữ state symbol/mode phù hợp; logo không biến thành nút giả.
- Mặc định page active `Mô phỏng lệnh` trong screenshot nghiệm thu; các trang khác vẫn nguyên chức năng.

### B. Header (top bar)
- Xếp theo chiều ngang: **LIVE / REPLAY / SYNTHETIC_TEST** segmented 3 pill; search mã có dữ liệu universe; date picker (active REPLAY); lựa chọn phiên (sáng/chiều/cả ngày); icon bell; avatar generic `Xin chào!` nếu app không quản lý user identity.
- Chỉ một mode ACTIVE, không vừa tô LIVE vừa chọn SYNTHETIC_TEST. Trạng thái collector `ONLINE/OFFLINE/STALE` là nhãn khác với mode, không giả định chọn LIVE là online.
- Header x-height 66 px, viền mờ, nút chuyển mode cập nhật tất cả view một cách atomically; search chỉ chọn mã có trong universe, mã chưa có quote vẫn được chọn với trạng thái `NO_DATA`.

### C. Hero — khu bắt mắt nhất
- Card y≈80–254, full width khu giữa, gradient như ảnh; chia trái ~57%, mascot ~43%.
- Text trái: H1 `Execution Lab`; dòng phụ `Hiểu thanh khoản và kiểm chứng quyết định giao dịch:`; dòng nhấn `Liệu một lệnh có thể được đáp ứng trong 3 mức giá?`.
- 3 tag ở chân: `⚡ Ước tính khả năng đáp ứng`, `🎯 Đo tác động giá`, `◈ Hỗ trợ quyết định`.
- Hình **gấu mèo 3D dễ thương** với tai, kính/áo tím, laptop tím; đặt ở phía phải, cao ~170–188px, giữ nguyên ratio, dùng file riêng `src/app/assets/mascot.png` nếu repo hiện có hoặc asset PNG/WebP được cung cấp; không copy nguyên screenshot làm ảnh hero; không để phần thân/đầu mất quá 15% vì crop. Background cloud shapes chỉ trang trí nhẹ.
- Mascot là **trang trí**, không gây hiểu nhầm mức độ an toàn giao dịch. Nếu dự án trước đó ẩn mascot thì **trang này theo chỉ định mới của người dùng phải hiện mascot như reference**; các trang khác không tự thêm mascot.

### D. Control Strip — Mô phỏng lệnh (y≈264–325)
- Một card ngang duy nhất, không rải mỗi input thành một card lớn.
- Thứ tự: icon mục tiêu + label `Mô phỏng lệnh` → `BUY` `SELL` (BUY active tím, SELL outline) → `Mã` + dropdown tìm toàn universe → `Khối lượng (CP)` number-input dạng stepper → CTA `▷ Mô phỏng ngay`.
- `requested_qty` phải **nguyên dương >0**, không ép thành bội 100 nếu app cho phép odd lot làm test; validate max hợp lý để bảo vệ hiệu năng nhưng không tự thay yêu cầu người dùng. Có thể mặc định `400` hoặc giá trị người dùng đang lưu, không hardcode số kết quả.
- Khi đổi mã: cập nhật snapshot/query/timeseries, reset `simulation_record` của mã cũ; tuyệt đối không giữ kết quả mã khác.
- Khi đổi BUY/SELL: BUY quét Ask1→Ask3; SELL quét Bid1→Bid3. Qty thay đổi thì compute lại khi bấm CTA hoặc live preview có nhãn rõ, nhưng không gọi REST/WS lại chỉ vì thay quantity.
- REPLAY: chọn ngày và thời điểm snapshot hợp lệ; LIVE: yêu cầu timestamp mới, status online; TEST: dữ liệu synthetic có nhãn DEMO.

### E. KPI Result Strip (y≈334–402)
- Một dải card liên tục với 5 phân vùng: `Kết quả mô phỏng` / `VWAP` / `Đáp ứng · CP` / `Chưa đáp ứng · CP` / `Price impact · bps` / `Coverage`. Ảnh có 6 text groups, có thể co 1 cột label nhỏ.
- `VWAP` = sum(level_price * filled_qty_level)/filled_total; nếu `filled_total=0` => `—`, không bằng 0.
- `Filled` = sum qty đã phân bổ trong 3 mức; `Unfilled=Requested−Filled`; `Coverage=Filled/Requested×100%`.
- Price impact bps: `(VWAP−Ask1)/Ask1*10000` với BUY; `(Bid1−VWAP)/Bid1*10000` với SELL, tức chi phí tương đối bất lợi, chỉ khi filled>0 và best quote hợp lệ; có thể đối chiếu công thức W4 hiện hành và giữ W4 canonical nếu đã khác.
- Không gọi `Price impact 0` chỉ vì không có dữ liệu; hiện `—` với reason.
- `Filled` là **khối lượng đáp ứng theo độ sâu quan sát**, không nói đã thực hiện lệnh thực tế.

### F. Natural-Language Insight Strip (y≈409–496)
- Card hồng nhạt/cream, icon bulb, phía phải có `2–3` ghi chú bằng biểu tượng xanh/cam; có thể đặt icon đầu mascot nhỏ như reference nếu giữ thiết kế.
- Text dựa trên **tính toán từ cùng snapshot**, ví dụ: `Với lệnh mua giả định {Q} CP {SYMBOL}, sổ lệnh L1–L3 ghi nhận khả năng đáp ứng {COV}% ({FILLED} CP); còn {UNFILLED} CP chưa đáp ứng trong phạm vi quan sát.`
- Nếu `filled == Q`: `Toàn bộ khối lượng nằm trong độ sâu L1–L3 đang quan sát`; nếu chỉ L1 thì nêu chỉ sử dụng mức giá tốt nhất; nếu quét sang L2/L3 thì nêu chênh lệch VWAP vs best price bằng bps.
- Nếu unfilled >0: `phần chưa đáp ứng nằm ngoài độ sâu quan sát; KHÔNG ước lượng giá ở L4`.
- Nếu LO/units/book chưa hợp lệ: không đưa ra lời khuyên, hiện `Không thể mô phỏng snapshot này` + lý do + CTA `Xem Data Trust / Chuyển sang Replay hợp lệ`.
- Không gán tên nhãn `thanh khoản rất tốt`, `dễ khớp` vô điều kiện; chỉ diễn giải định lượng dưới phạm vi 3 mức và ghi rõ không đảm bảo khớp lệnh thật.

### G. Chart Row 1 — 3 cards cạnh nhau
1. **Depth Mirror · Quan sát** (rộng ~1/3): Bên trái Bid tím, phải Ask peach; thể hiện depth tích lũy của L1–L3 hoặc bars rõ theo mức; x-axis **Giá · VND/CP**, y-axis **Khối lượng · CP**; hover hiển thị `L1/L2/L3, giá, qty tại mức, cumulative qty`. Các cặp [0,0] là mức trống hợp lệ theo SSI; biểu đồ không vẽ điểm giá 0 như mức thanh khoản thị trường.
2. **Sweep Allocation**: donut/pie L1, L2, L3, `Chưa đáp ứng`; tổng các phần **bằng Q**. Tooltip show giá/qty/%; phần chưa đáp ứng màu peach/coral và **không được có label `L4`**. Nếu không có filled, vòng tròn thể hiện unfilled 100% với thông báo.
3. **Coverage Curve**: x=quantity giả định, y=coverage%; tính từ snapshot đang chọn, dựa trên 3 mức theo side, tối đa 100%; đường phải **không tăng khi Q tăng trên cùng book**. Đường dọc marker `Q người dùng nhập` và tooltip exact coverage.

### H. Chart Row 2 — 2 cards cạnh nhau
4. **Spread Timeline · Quan sát**: x=timestamp quote thật theo VN(+07); y=spread bps (đơn vị ghi rõ bps). Dùng khoảng thời gian có dữ liệu thực, không vẽ fake sawtooth. Nếu gap >60 giây (cấu hình), ngắt đường, không nối xuyên downtime. Khi LIVE chưa verified, chỉ dùng snapshot được phép hiển thị quan sát theo policy, gắn nhãn data quality.
5. **OBI Timeline · Quan sát**: bar chart có baseline 0, range [-1,1], OBI>0 plum/mint, OBI<0 blush/coral; tooltip có `BidDepth, AskDepth, OBI` + timestamp. Cần depth sum>0, tránh 0/0; không nói OBI âm chắc chắn khiến giá giảm.
- Hai chart có shared time window, cùng symbol/mode/snapshot filter. Mọi chart thiếu data phải có empty-state lý do và bước tiếp theo, không render chart hư/dữ liệu từ mã trước.

### I. Formula Expander (cuối giữa)
- Dòng title `Công thức & giới hạn mô phỏng`, icon sách mở, icon dropdown; khi mở có các công thức Spread (absolute + bps), Depth_3, OBI, Coverage, VWAP_filled, price impact và mô tả hạn chế: queue priority, partial fills, thanh khoản ẩn, thay đổi book trong khi giả lập, fees/taxes không được tính.
- Gắn link/dòng `Nguồn: SSI FastConnect; mode {MODE}; snapshot {ID}; giờ Việt Nam; policy verification version`.

### J. Right Rail — ba card dọc
**J1 Watchlist** (~285 px): title `Watchlist của bạn` và `Xem tất cả`; tối đa 5 mã ưu tiên (ví dụ FPT/VPB/SSI/HPG/VNM) có thể tùy chỉnh. Mỗi dòng `☆` `mã` `giá` `thay đổi%` `liquidity status` nếu các trường lấy được và có timestamp nguồn; khi chưa có dữ liệu để tính trạng thái thì hiện `Chưa đánh giá`. Giá REST lịch sử phải ghi `REST · dd/mm/yyyy`, tuyệt đối không làm như giá LIVE. Click mã đổi toàn app, không tự subscribe 230 mã ngay từ Watchlist.
**J2 Session Snapshot** (~225 px): time range quan sát, `Avg Spread (bps)`, `Avg OBI`, `Snapshot đạt điều kiện x/y`, số giây quan sát (có dấu mốc thiếu), không gọi dữ liệu 30 phút là đủ cả buổi. Các tỷ lệ phải có mẫu số rõ và có thể click xem QA.
**J3 Data Trust** (~160 px): status `LIVE_VALID / REPLAY_VALID / SYNTHETIC_TEST / NO_DATA / OFFLINE / STALE / BLOCKED`, 3–5 check điểm: verified price/qty, full snapshot, effective market.flag đúng sàn, provenance/recency, WS connection. Nếu đang REPLAY không hiển thị badge `LIVE` làm trạng thái nguồn hiện tại. Có CTA `Chi tiết Data Trust`.

## 4. DATA BINDING & STATE — TOÀN BỘ UI DÙNG CÙNG SNAPSHOT

Đọc state thực trong `src/app/state.py` (hoặc repo hiện hành). Các biến logic tối thiểu: `selected_symbol`, `mode` (`LIVE`, `REPLAY`, `SYNTHETIC_TEST`), `selected_date`, `selected_snapshot_id`, `trade_side` (`BUY`,`SELL`), `requested_qty`, `selected_session`, `collector_status`, `validation_status`.

**Không trộn nguồn:**
- **LIVE:** những quote SSI thực mới nhất, collector đang kết nối, snapshot+flag+unit+book eligible; readback đầy đủ; tự refresh giới hạn ~5–10 giây (hoặc theo logic app), không bật tính khi stale/offline.
- **REPLAY:** đọc quote LIVE đã lưu (không cần collector online), ngày/timestamp/snapshot ID đúng, đúng `market.flag` lịch sử; cho phép tua và dùng snapshot trong mô phỏng; quote chưa qualified chỉ cho quan sát đủ ràng buộc, không mô phỏng.
- **SYNTHETIC_TEST:** fixture cố định/có seed, hỗ trợ mọi symbol hợp lệ trong universe, ghi nhãn DEMO mạnh và không hiển thị giá demo như giá SSI thật. Dùng để test edge cases, không xuất làm bằng chứng LIVE.
- **HISTORICAL OHLCV:** dùng để vẽ giá/volume lịch sử ở trang Market Pulse/Chart Studio hoặc thẻ bổ sung, **không** dùng để tự chế Bid/Ask 3 mức; lịch sử có thể hiển thị độc lập LIVE gate.

**SSI evidence** đã được user nhận bằng email: Giá Quote **VND**, khối lượng Quote **số cổ phiếu**, bản tin Quote phiên bản hiện tại là **toàn bộ Bid/Ask**, mức trống `['0','0']`. Chỉ áp dụng mapping này cho payload/phiên bản có định dạng thực sự tương thích; ghi `evidence_ref`, `normalizer_version`. Không áp dụng hệ số x1000 tùy tiện.

**State invalidation:** Khi đổi symbol/mode/date/snapshot reset mọi kết quả mô phỏng không còn khớp. Replay giữ time; khi đổi qty/sell thì tính từ quote đã chọn; Chart Timeline cùng cửa sổ và cùng data quality policy. Khi data missing, hiển thị `NO_DATA` và nguyên nhân theo từng module, không lặp placeholder tối nghĩa.

**Performance:** >300k quote nhiều mã trong SQLite hiện là dữ liệu lớn với browser; chỉ SQL query `WHERE symbol=? AND date/time window`, dùng index `(symbol, quote_time, mode)`, phân trang/limit timeline, làm downsampling cho plot 500–2000 điểm khi cần; không load toàn bộ JSONL/SQLite sang Streamlit hoặc Safari khi rerun; cache có invalidation theo file mtime/count hoặc revision.

## 5. THỨ TỰ SỬA FILE — PHÙ HỢP REPO

- `src/app/styles.py`: tokens, full-page responsive grid, CSS scoped; giữ UI khác không vỡ.
- `src/app/components.py`: sidebar, topbar, hero, simulation-control, kpi-results, explain, right watchlist/snapshot/trust cards, empty/error state.
- `src/app/pages.py`: trang `simulator(...)` theo cấu trúc đã khóa; nếu Dashboard home vẫn đang chứa components thì chỉ migrate layout tương ứng, không phá các tab.
- `src/app/charts.py`: không tự thay công thức W4; sửa color/tooltip/depth/donut/coverage/chart ranges.
- `src/app/view_models.py` và `src/app/state.py`: adapter/query có giới hạn/tính nhất quán/mode/symbol/freeze snapshot, không dùng `SYNTHETIC_TEST` để che thiếu data LIVE.
- `src/app/dashboard.py`: render routing và reactivity, dùng entrypoint cũ.
- `src/app/assets/mascot.png`: tái dùng nếu có; không cần image generation bổ sung nếu asset đã đầy đủ.
- `tests/`: UI key state test; `test_finance_examples.py`, `test_dashboard.py`, `test_dashboard_all_symbols_and_history.py`, test new scenario (see below).

**Không chạm đến module `src/ssi_api` và `src/data/raw` khi chỉ thực hiện thiết kế**, trừ khi phát hiện bug ảnh hưởng read-only adapter và được giải thích chính xác. Không ghi đè hoặc xóa `.env`, `quotes.sqlite`, JSONL đã thu hoặc SQLite OHLCV.

## 6. RESPONSIVE

- ≥1440px: giữ sidebar 228px, center + right rail như ảnh, charts 3+2, hero mascot phải.
- 1100–1439px: sidebar còn 72–190px tùy width, center tách chart grid 2 cột, right rail nhỏ 280–320px hoặc xuống dưới nếu thiếu chỗ; controls có thể wrap 2 dòng.
- 760–1099px: right rail chuyển xuống dưới, main full còn lại, chart grid 2+1, margin 12px.
- <760px: sidebar thành hamburger/drawer, data controls stack, one chart per row, number labels không tràn, không che CTA.
- Nút phải accessible, contrast 4.5:1 cho body nếu có thể, focus/hover rõ; tooltip `i` có nội dung thật. Những giá trị âm được ghi dấu và đơn vị chính xác.

## 7. CHECKLIST NGHIỆM THU KỸ THUẬT

### Visual (phải screenshot)
- Render screenshot tại **1672×941** sau khi dữ liệu được chọn; so sánh side by side cùng `REFERENCE_EXECUTION_LAB_MASCOT.png`.
- Sidebar x≈0–228, hero y≈80–254, center width≈986, right rail≈415, control/result/explain/chart rows đúng thứ tự; sai lệch position khoảng 8–12px có thể chấp nhận vì font/Streamlit; không có horizontal scroll.
- Màu HEX đúng bộ tokens; font đọc được tiếng Việt; mascot nằm bên phải hero đúng tỷ lệ, không mất tay/tai; card radii/shadows giống ảnh.
- Chart labels đều thấy ở viewport; không dùng screenshot reference như ảnh nền cả UI.

### Functionality (bắt buộc test)
1. `SYNTHETIC_TEST, FPT, BUY Q=400`: tính từ fixture thực, không hardcode 100.000/98.6%; tất cả chart theo FPT, mode TEST.
2. `SYNTHETIC_TEST, FPT, SELL Q=400`: sweep từ Bid, không dùng Ask, same symbol.
3. `Q > total available 3-level depth`: `unfilled>0`, coverage<100, VWAP trên phần filled, không khẳng định L4.
4. `Q <= L1 available`: chỉ L1, impact=0 theo best price, coverage=100.
5. `Q>0` rule; Q=0/âm/chuỗi lỗi -> không mô phỏng, hiển thị validation.
6. Nếu `['0','0']` ở mức giá trống, không coi là quote hỏng toàn bộ; bỏ qua liquidity rỗng, ghi trạng thái quan sát chính xác theo validation.
7. `REPLAY` chọn đúng mã/ngày/snapshot ở data thực; bỏ qua collector offline nhưng không bỏ qua provider/flag/unit/book checks.
8. `LIVE` collector OFFLINE: không hiện kết quả giả như Live; hiển thị empty state, cho phép xem REPLAY/TEST.
9. LIVE snapshot có market flag từ sai board hoặc sau reconnect chưa xác minh: block simulation và giải thích tại Data Trust.
10. Đổi symbol FPT → HPG: toàn bộ KPI + 5 chart + insights chỉ chứa HPG, không giữ data FPT cũ; nếu HPG không có quote, card NO_DATA rõ ràng.
11. Watchlist giá REST dùng đúng provenance/time, không lẫn với VWAP synthetic.
12. Spread bps chính xác, OBI trong [-1,1], coverage(Q) không tăng khi tăng Q trong cùng book, sum donut segments = Q.
13. Gaps time >60s không bị nối thành đường liên tục; timezone Asia/Ho_Chi_Minh; ngày 19/11/2026 trong lịch sử không bị thay bằng 2024 vì concept.
14. Source statuses không mâu thuẫn: chọn REPLAY thì top REPLAY active và Data Trust hiển thị REPLAY_VALID, không tự bật LIVE.
15. Browser Chrome/Safari test với ít nhất 1 mã có quote, 1 mã missing, 1 mã có mức 0, 1 mã chỉ synthetic; không crash khi lượng quote lớn.
16. Export JSON/CSV nếu có phải gồm `provider, mode, symbol, snapshot_id, quote_time, side, Q, filled, unfilled, VWAP, coverage, impact, evidence/validation`.
17. pytest hiện tại đạt sau sửa; không xóa các tests khó để đạt PASS.

## 8. QUY TRÌNH CODEX 6 PHASES (LÀM XONG TỪNG PHASE MỚI CHUYỂN)

**PHASE 1 — AUDIT:** đọc repo và xác định component/code routes; chụp current screenshot; note những phần sẽ sửa và backup. Không thay finance/data modules.

**PHASE 2 — DESIGN SYSTEM:** lập tokens CSS, grid, sidebar, topbar, hero + mascot, cards placeholders theo **đúng vùng**; chụp screenshot viewport chuẩn; so sánh reference. Chưa vội đổi thuật toán, không chỉnh API SSI.

**PHASE 3 — DATA BINDINGS:** nối controls/state/quote adapter; kết quả KPI, explanations, Data Trust, right rail lấy dữ liệu; không hardcode.

**PHASE 4 — CHARTS:** triển khai 3+2 layout, Plotly thật, hover, row height/axis, gaps, missing data. Không lấy lịch sử nến làm book.

**PHASE 5 — QA:** chạy tests, kiểm tra edge-cases ở mục 7, benchmark page với dữ liệu 201–230 mã, kiểm tra Safari không nạp tất cả 300k quote; screenshot compare và sửa lệch pixel.

**PHASE 6 — DELIVERY:** báo file changed, screenshots BEFORE/AFTER, test pass/skip/fail, các giới hạn chưa khắc phục, hướng dẫn chạy `PYTHONPATH=src streamlit run src/app/dashboard.py`; giữ dữ liệu RAW/SQLite không đổi.

## 9. Definition of Done — TIÊU CHUẨN KHÔNG CHẤP NHẬN LÀM NỬA VỜI

- Về **visual**: screenshot ở 1672×941 thể hiện rõ đúng 7 khối trung tâm và 3 right cards, màu/mascot/typography bo góc sát reference, không bị thừa khối đẩy chart ra khỏi bố cục.
- Về **state**: không mã nào bị giới hạn cứng cho user select; quote missing khác synthetic available; LIVE/REPLAY/TEST không lẫn.
- Về **finance**: công thức W4 không đổi sai, chỉ simulate L1–L3, không giả định khớp thật hoặc giá L4.
- Về **data**: evidence units của SSI được giữ, no fake flag, no “100% valid” khi chỉ có ít phút quan sát; giữ source timestamps.
- Về **performance**: trang không crash và không load toàn bộ rows của mọi mã.
- Về **handoff**: mọi controls có tác dụng; screenshot + tests + filelist + remaining limits được bàn giao minh bạch.

**Nếu có xung đột giữa ảnh (số liệu đẹp, trạng thái LIVE) và dữ liệu/công thức thực, ưu tiên sự đúng đắn dữ liệu; nhưng giữ hình thức UI của ảnh.**

## 10. Ưu tiên khi repo còn bản đặc tả UI cũ

Trong các bản dự án đã trao đổi trước đây, `docs/ui_reference/reference_dashboard.png` và `MASTER_SPEC_LIQUIDITYGUARD.md` có thể mô tả **một layout khác** (6 KPI nằm trên hero, sidebar hẹp 72px, hero cao hơn). **Khi xây trang `Execution Lab` lần này, phải dùng `REFERENCE_EXECUTION_LAB_MASCOT.png` và tài liệu này là chuẩn cao nhất**; tuyệt đối không pha trộn layout cũ vào trang này. Các file cũ chỉ tham khảo về backend và hệ thống màu nếu không xung đột.

Trong bản repo đã xem, `src/app/pages.py` có hai hàm `dashboard(...)` và `simulator(...)`; **mục tiêu của yêu cầu lần này là `simulator(...)` (Mô phỏng lệnh)**, không phải thay trang `dashboard(...)` thành concept mới. Nếu `hero()` / `trade_strip()` là shared component, có thể dùng variant hoặc scoped wrapper (`variant="execution_lab"`) để thay giao diện trang Simulator mà không làm hỏng Dashboard/Market Pulse.
