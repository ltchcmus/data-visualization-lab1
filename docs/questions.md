# Danh sách câu hỏi phân tích

**Bài toán chung:** Phân tích các yếu tố ảnh hưởng đến hiệu quả bán hàng của sách trên nền tảng trực tuyến Nhà sách Tiki

**Biến mục tiêu:** `all_time_quantity_sold`

---

## Câu 1 — Phân bổ doanh số (Công)

**Câu hỏi:** Phân tích phân bổ doanh số (`all_time_quantity_sold`) của các đầu sách nhằm xác định liệu doanh thu có tập trung vào một số ít sản phẩm bán chạy hay phân tán đều, từ đó làm rõ mức độ tồn tại của hiệu ứng long-tail trong dataset hiện tại.

**Mục tiêu:** Sử dụng biểu đồ Histogram và thang đo log để phân tích phân phối doanh số của 36.808 đầu sách, nhằm xác định liệu mô hình kinh doanh có tuân theo quy luật Pareto (20/80) hay không, từ đó đề xuất 03 chiến lược quản lý kho bãi cho nhóm sách "ngách" (long-tail) trước khi kết thúc tuần 6

**Nhận xét:**
Sự tồn tại rõ rệt của Hiệu ứng Long-tail: Biểu đồ cho thấy một phân phối lệch phải cực kỳ lớn.
Đại đa số các đầu sách tập trung ở nhóm có lượng bán thấp (gần trục 0), tạo thành "cái đuôi dài" kéo dài về phía bên phải.
Giá trị của Thang đo Log: Nhờ việc áp dụng $log(y)$, chúng ta có thể quan sát được sự hiện diện của các nhóm sách bán được
từ 1.000 đến hơn 3.500 bản. Nếu sử dụng thang đo tuyến tính, các nhóm này sẽ bị lu mờ hoàn toàn bởi nhóm sách có doanh số thấp,
khiến chúng ta bỏ lỡ các phân khúc "Best-seller".
Điểm đột biến ở cuối trục (Outliers): Có một sự gia tăng bất thường về số lượng đầu sách ở mốc doanh số cao nhất (>3.500 bản).
Đây là nhóm sản phẩm "ngôi sao", đóng góp tỷ trọng doanh thu vượt trội so với phần còn lại của danh mục.
Mật độ dữ liệu: Khoảng cách giữa các cột ở phần đuôi thưa dần, cho thấy ở các mức doanh số cao,
sự cạnh tranh giữa các đầu sách trở nên ít hơn nhưng giá trị mỗi đầu sách mang lại lại lớn hơn rất nhiều.
**Kết luận:** Việc phân tích đã làm rõ bài toán về hiệu quả bán hàng thông qua cấu trúc doanh số:Về mô hình kinh doanh: Dataset hiện tại minh chứng cho quy luật Pareto: Doanh thu của nhà sách phụ thuộc lớn vào một nhóm nhỏ các đầu sách bán chạy (Head), nhưng sự đa dạng của hàng nghìn đầu sách ngách (Tail) chính là yếu tố tạo nên độ phủ thị trường.Về chiến lược: \* Nhóm Head: Cần ưu tiên các chiến dịch marketing mạnh mẽ và đảm bảo tồn kho liên tục vì đây là nguồn thu chính.Nhóm Tail: Cần áp dụng hệ thống gợi ý (Recommendation System) thông minh để kết nối các sản phẩm ngách này tới đúng tệp khách hàng mục tiêu mà không tốn quá nhiều chi phí quảng cáo đại trà.Độ tin cậy: Việc xác định được "Cái đuôi dài" giúp nhóm khẳng định dataset đủ độ phức tạp và tính thực tế để thực hiện các phân tích sâu hơn ở các tab tiếp theo.

**Biểu đồ:** Histogram + Log scale

| Trục | Cột                      |
| ---- | ------------------------ |
| X    | `all_time_quantity_sold` |
| Y    | frequency (log scale)    |

**Ghi chú:** Dễ nhìn nhận ra long-tail.

---

## Câu 2 — Hiệu quả bán hàng theo danh mục (Công)

**Câu hỏi:** Phân tích sự khác biệt về hiệu quả bán hàng giữa các mục (categories) nhằm xác định xem mục nào sẽ tiềm năng doanh số trên dataset này.
**Mục tiêu:** Phân tích hiệu quả bán hàng của 15 thể loại sách hàng đầu để xác định ít nhất 2 danh mục 'Tiềm năng (Niche)' có mức Rating trung bình >4.8 và doanh số ổn định (thể hiện qua biểu đồ phân vùng danh mục) nhằm đề xuất chiến lược nhập hàng tập trung trước cuối kỳ

**Biểu đồ:** Boxplot

| Trục | Cột                      |
| ---- | ------------------------ |
| X    | `cat_level_2` (category) |
| Y    | `all_time_quantity_sold` |

**Ghi chú:** Không chỉ biết "cái nào cao", mà còn biết: ổn định hay không, có outlier (best seller) không.

---

## Câu 3 — Nhà xuất bản có doanh số cao nhất (Đề)

**Câu hỏi:** Nhà xuất bản (`publisher_vn`) nào có doanh số trung bình cao nhất? Liệu có sự tập trung doanh số vào một vài NXB lớn hay thị trường phân tán đều giữa các NXB?

**Biểu đồ:** Horizontal Bar Chart (Top N)

| Trục | Cột                                 |
| ---- | ----------------------------------- |
| X    | `all_time_quantity_sold` trung bình |
| Y    | `publisher_vn` (top 15–20 NXB)      |

**Ghi chú:** Sắp xếp giảm dần để dễ so sánh. Có thể thêm đường trung bình toàn dataset để thấy NXB nào vượt ngưỡng. Lưu ý lọc bỏ các NXB có quá ít đầu sách (< 5) để tránh bias.

---

## Câu 4 — Tác giả đóng góp vào tổng doanh số (Đề)

**Câu hỏi:** Tác giả nổi tiếng đóng góp như thế nào vào tổng doanh số? Liệu 20% tác giả hàng đầu có tạo ra 80% lượng bán, và sự thành công của họ đến từ một vài siêu phẩm hay từ sự ổn định đều tay trên toàn bộ danh mục tác phẩm?

**Biểu đồ:** Biểu đồ Pareto hoặc Boxplot

| Thành phần | Chi tiết                                                                                                   |
| ---------- | ---------------------------------------------------------------------------------------------------------- |
| Pareto     | X: tác giả sắp xếp giảm dần theo tổng `all_time_quantity_sold`; Y trái: tổng lượng bán; Y phải: % tích lũy |
| Boxplot    | Mỗi box là một tác giả top (10–15), thể hiện phân phối doanh số các đầu sách                               |

**Ghi chú:** Pareto kiểm tra quy tắc 80/20. Boxplot phân biệt tác giả "bán đều" vs tác giả "một hit duy nhất".

---

## Câu 5 — Ngưỡng giảm giá tác động đến doanh số (Hiểu)

**Câu hỏi:** Có tồn tại một ngưỡng giảm giá nào mà tại đó doanh số tăng vọt không? Hay sự tương quan giữa Tỷ lệ giảm giá (`discount_rate`) và Doanh số (`all_time_quantity_sold`) là tuyến tính?

**Mục tiêu:** Xác định ngưỡng giảm giá tối ưu trong các dải từ 0% đến >75% để tìm ra mức chiết khấu giúp đạt tỷ trọng doanh thu cao nhất và đánh giá tính phi tuyến tính của mối quan hệ này trước khi kết thúc giai đoạn phân tích dữ liệu.

**Biểu đồ:** Bar + Line (dual axis)

| Thành phần | Chi tiết                           |
| ---------- | ---------------------------------- |
| Bar        | Số lượng bán ra theo nhóm discount |
| Line       | Tỷ lệ giảm giá trên trục Y phụ     |

**Ghi chú:** Sử dụng biểu đồ kết hợp với cột (Bar) thể hiện số lượng bán ra và đường (Line) thể hiện tỷ lệ giảm giá. Việc đặt hai yếu tố này cùng một trục thời gian hoặc danh mục sách sẽ giúp xác định các điểm nơi mức giảm giá mang lại hiệu quả chuyển đổi cao nhất.

---

## Câu 6 — Quy tắc 80/20 tác giả (Hiểu)

**Câu hỏi:** Dựa trên quy tắc 80/20, những tác giả nào đang đóng góp phần lớn vào tổng giá trị giao dịch của cửa hàng? Sự thành công của họ đến từ một vài siêu phẩm hay từ sự ổn định của toàn bộ danh mục tác phẩm?

**Biểu đồ:** Biểu đồ Pareto

**Ghi chú:** Kết hợp các cột doanh thu (Giá thực tế × Số lượng đã bán) được sắp xếp giảm dần và đường tích lũy phần trăm. Biểu đồ không chỉ vinh danh các tác giả mang lại doanh thu lớn nhất mà còn giúp xác định nhóm tác giả ưu tiên cần tập trung nguồn lực marketing.

---

## Câu 7 — Rating vs Review_count (Thịnh)

**Câu hỏi:** Khách hàng quan tâm đến "Điểm số chất lượng" (`rating_average`) hay "Số lượng người đã mua/đánh giá" (`review_count`) hơn khi đưa ra quyết định mua hàng? Sự cộng hưởng giữa hai yếu tố này tạo ra đột phá doanh số như thế nào?

**Biểu đồ:** Bubble chart hoặc Correlation Heatmap

| Thành phần | Chi tiết                                                                                      |
| ---------- | --------------------------------------------------------------------------------------------- |
| Bubble     | X: `rating_average`; Y: `review_count`; kích thước bong bóng (size): `all_time_quantity_sold` |
| HeatMap    | Thể hiện hệ số tương quan giữa các biến số lượng                                              |

**Ghi chú:** Thể hiện hệ số tương quan giữa các biến số lượng (giá, điểm đánh giá, số lượt đánh giá, lượt bán) để có cái nhìn tổng quát bằng số liệu.

---

## Câu 8 — Freeship & Seller lớn (Thịnh)

**Câu hỏi:** Việc sách được phân phối bởi các nhà cung cấp lớn (ví dụ: Tiki Trading) hoặc đi kèm chính sách giao hàng miễn phí (`has_freeship`) tạo ra lợi thế cạnh tranh doanh số lớn đến mức nào so với các nhà bán lẻ khác?

**Biểu đồ:** Violin plot hoặc Boxplot

| Trục | Cột                                                   |
| ---- | ----------------------------------------------------- |
| X    | `has_freeship` True/False hoặc top 5 `current_seller` |
| Y    | phân bổ của `all_time_quantity_sold` (log scale)      |

**Ghi chú:** Biểu đồ này vừa cho thấy mức trung vị, vừa cho thấy độ phân tán của lượng bán. Có thể dùng thang đo log để giảm thiểu tác động của outliers.

---

## Câu 9 — Xu hướng doanh số theo năm xuất bản (Đề)

**Câu hỏi:** Phân tích sự ảnh hưởng của discount đến sales: Discount có thực sự làm sách xuất bản gần đây có lợi thế doanh số hơn sách cũ không? Xu hướng lượng bán thay đổi theo năm xuất bản (`publication_date`) như thế nào?

**Mục tiêu:** So sánh hiệu quả doanh số của nhóm sách mới xuất bản (2020–2025) so với nhóm sách cũ dựa trên xu hướng lượng bán và giá bán trung bình, nhằm chứng minh liệu việc giảm giá bán có thực sự tạo ra ưu thế doanh số vượt trội cho sách mới hay không.

**Biểu đồ:** Bar Chart theo năm + đường trung bình động

| Trục | Cột                                 |
| ---- | ----------------------------------- |
| X    | năm xuất bản (nhóm theo năm)        |
| Y    | `all_time_quantity_sold` trung bình |

**Ghi chú:** Giúp thấy sách mới hay sách kinh điển lâu năm bán tốt hơn. Lưu ý: sách cũ có nhiều thời gian tích lũy đơn hàng hơn → cần chuẩn hóa nếu muốn so sánh chính xác so với tang sales?

---

## Câu 10 — Độ dày sách vs Doanh số (Đề)

**Câu hỏi:** Độ dày của sách (`number_of_page`) có tương quan với doanh số không? Người mua có xu hướng chọn sách ngắn gọn hay sách dài nội dung?
Xác định mối tương quan giữa số trang và doanh số để kết luận liệu nhóm sách có độ dày từ 100–300 trang có chiếm ưu thế về lượng bán (doanh số >1000 bản) so với các nhóm khác hay không, từ đó tối ưu hóa tiêu chí chọn lựa sản phẩm

**Biểu đồ:** Scatter Plot + đường hồi quy

| Trục | Cột                                                               |
| ---- | ----------------------------------------------------------------- |
| X    | `number_of_page` (nhóm theo khoảng: <100, 100–300, 300–500, >500) |
| Y    | `all_time_quantity_sold`                                          |

**Ghi chú:** Dùng log scale cho trục Y do phân phối lệch. Scatter plot thể hiện xu hướng tổng thể, đường hồi quy cho thấy chiều hướng tương quan (dương/âm/không rõ).

## Câu 11 — Hiệu quả của "Combo" (Giá & Rating)

Câu hỏi: Phân khúc giá nào là "điểm ngọt" (sweet spot) mà khách hàng sẵn sàng bỏ qua yếu tố Rating thấp? Hay nói cách khác, giá rẻ có bù đắp được cho chất lượng kém không?

Biểu đồ: Heatmap (X: Khoảng giá, Y: Khoảng Rating, Màu sắc: Tổng lượng bán).

## Câu 12 — Phân tích "Sách kén người đọc" (Niche Market)

Câu hỏi: Có những danh mục nào có lượng bán thấp nhưng Rating lại rất cao? Đây có phải là thị trường ngách tiềm năng để đầu tư marketing không?

Biểu đồ: Scatter Plot với đường trung bình (Quadrant Chart) chia làm 4 vùng: Ngôi sao (High Sales/High Rating), Tiềm năng (Low Sales/High Rating), Phổ thông (High Sales/Low Rating) và Cần cải thiện.

---

## Tổ chức theo Tab Dashboard

| Tab                           | Câu hỏi      | Chủ đề                                  |
| ----------------------------- | ------------ | --------------------------------------- |
| Tab 0 — Tổng quan             | Q1           | Tổng quan thị trường & KPI chính        |
| Tab 1 — Sản phẩm              | Q2, Q10, Q12 | Đặc tính vật lý & Phân loại             |
| Tab 2 — Giá & Chiết khấu      | Q5, Q9, Q11  | Tác động của giá, chiết khấu, thời gian |
| Tab 3 — NXB & Tác giả         | Q3, Q4/Q6    | Nhà xuất bản, tác giả                   |
| Tab 4 — Đánh giá & Chính sách | Q7, Q8       | Rating, review, freeship, seller        |
