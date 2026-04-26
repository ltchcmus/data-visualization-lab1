# Trực quan hóa dữ liệu - Đồ án Lab 1

## PlotTwist - Phân tích dữ liệu sách trên nền tảng Tiki

Đồ án thực hiện thu thập dữ liệu, xử lý dữ liệu, trực quan hóa và xây dựng mô hình học máy (dự báo doanh số và phân cụm sản phẩm) cho bài toán phân tích các yếu tố ảnh hưởng đến hiệu quả bán hàng của sách trên nền tảng thương mại điện tử Tiki.
Bao gồm các bước: **Crawl dữ liệu, tiền xử lý dữ liệu, trực quan hóa dữ liệu, ứng dụng mô hình học máy và xây dựng Dashboard tương tác**.

- Notebook phân tích và mô hình: `./notebooks`
- Mã nguồn xây dựng Dashboard: `./src/dashboard`
- Dependencies: `requirements.txt`
- Link truy cập Dashboard: https://group7-lab1.streamlit.app

---

## 1. Thông tin nhóm

- Nguyễn Hưng Thịnh (23120200)
- Lê Thành Công (23120222)
- Lê Thượng Đế (23120232)
- Vũ Nguyễn Trung Hiếu (23122028)
- Phan Ngọc Quân (23122046)

---

## 2. Cấu trúc project

```text
data-visualization-lab1/
├── data/
│   ├── processed/
│   └── raw/
├── docs/
├── notebooks/
│   ├── EDA/
│   ├── model/
│   └── preprocessing/
├── src/
│   ├── dashboard/
│   ├── data_collection/
│   └── insight_plugin/
├── config.yaml
├── main.py
├── requirements.txt
└── README.md
```

---

## 3. Pipeline xử lý dữ liệu & Xây dựng ứng dụng

### 1. Thu thập và Tiền xử lý dữ liệu

- Thu thập dữ liệu sản phẩm sách từ nền tảng Tiki.
- Xử lý dữ liệu bị khuyết, dữ liệu ngoại lai và chuẩn hóa thông tin cho phù hợp.

### 2. Trực quan hóa dữ liệu

- Xu hướng doanh số bán hàng và chính sách giá theo tuổi đời của sách.
- Đánh giá hiệu suất của tác giả và nhà xuất bản (Ứng dụng quy tắc 80/20).
- Tác động của đánh giá (rating/review) và hiệu ứng đám đông đến sức mua.
- Phân tích chiến lược vận hành (Seller) và hiệu ứng Freeship.
- Đánh giá lượng phân phối sản phẩm và rủi ro lưu kho (Long-tail effect).

### 3. Học máy và Dashboard

- Xây dựng mô hình Học máy (Random Forest Regressor) để dự báo doanh số.
- Ứng dụng K-Means Clustering để phân cụm và phân khúc thị trường sản phẩm.
- Phát triển ứng dụng Web Dashboard tương tác với Streamlit.
- Tích hợp AI Plugin (LLM) để tự động sinh Insight từ kết quả biểu đồ của dữ liệu.

---

## 4. Hướng dẫn cài đặt môi trường

- Yêu cầu môi trường: Python >= 3.10
- Yếu cầu phải tải trước folder data trên drive: [data-on-drive](https://drive.google.com/drive/folders/11GMwRh89sUaNiGqwADPY9f7EjX-etYgG?usp=sharing)

### 4.1. Cách 1 - Sử dụng venv

```bash
# Tạo môi trường
python -m venv .venv

# Kích hoạt (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
# Hoặc (Linux/macOS)
source .venv/bin/activate

# Cài đặt thư viện
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.2. Cách 2 - Sử dụng uv

```bash
# Cài đặt uv (nếu chưa có)
pip install uv

# Tạo và kích hoạt môi trường
uv venv .venv
# Kích hoạt trên Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Kích hoạt trên Linux/macOS: source .venv/bin/activate

# Cài đặt thư viện
uv pip install -r requirements.txt
```

---

## 5. Cách chạy project

### Khởi động Data Dashboard

```bash
streamlit run src/dashboard/app.py
```

Sau khi chạy, mở trình duyệt theo địa chỉ được hiển thị (thường là: `http://localhost:8501`)

### Quan sát các Notebook phân tích chi tiết

Mở thư mục `notebooks/` trong Jupyter Notebook / Jupyter Lab / VSCode để chạy từng bước cho quy trình EDA, Preprocessing và Model Selection.
