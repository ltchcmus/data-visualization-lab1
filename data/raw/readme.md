# Quy trinh crawl data (raw)

Thu muc nay chua du lieu chua qua tien xu ly, lay truc tiep tu Tiki API.
Du lieu hien tai lay tu Nha Sach Tiki, nen toan bo du lieu deu la ve sach

## 1) Chuan bi

- Mo terminal tai thu muc goc project: `data-visualization-lab1`
- Cai dependency:

```bash
pip install -r requirements.txt
```

## 2) Chay crawl danh muc sach

Script crawl chinh nam o [src/data_collection/crawler.py](src/data_collection/crawler.py) va mac dinh crawl danh muc:

- category_name: `nha-sach-tiki`
- category_id: `8322`

Chay lenh:

```bash
python ./src/data_collection/crawler.py
```

## 3) Du lieu tao ra sau khi crawl

Du lieu duoc luu duoi [data/raw](data/raw) theo cau truc danh muc con. Moi nhanh danh muc thuong co:

- `product.csv`: thong tin san pham da chuan hoa
- `product.txt`: raw JSON san pham
- `product-id.txt`: danh sach ID da lay
- `reviews.csv`, `customers.csv`, `buy_historys.csv`: du lieu danh gia va khach hang
- `checkpoint.json` / `product_checkpoint.json` / `reviews_checkpoint.json`: trang thai de resume

## 4) Co che resume neu bi ngat

Script co luu checkpoint, nen khi chay lai se bo qua phan da crawl.

- Neu muon tiep tuc: chay lai lenh o buoc 2.
- Neu muon crawl lai tu dau mot nhanh: xoa file checkpoint trong nhanh do roi chay lai.

## 5) Gom tat ca product.csv ve 1 file raw tong

Sau khi crawl xong, co the gom tat ca file `product.csv` thanh 1 file:

```bash
python ./src/data_collection/build_product_dataset.py --data-dir ./src/data_collection/data --output ./data/raw/book_dataset.csv
```

Ghi chu:
- Thay doi duong dan --data-dir va --output phu hop
- Hien tai co crawl them cac file review.csv nhung chua su dung
