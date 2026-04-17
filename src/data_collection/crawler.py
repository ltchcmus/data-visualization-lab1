import requests
import json
import csv
import os
from pathlib import Path
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytz
import pandas as pd
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import logging

# Cấu hình logging
logging.basicConfig(
    filename="crawl_tiki.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

product_url = "https://tiki.vn/api/v2/products/{}"
headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_1_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36"
}
ENABLE_REVIEW_CRAWL = False
LOG_FILE = Path("crawl_tiki.log")
MAX_WORKERS = 8
CATEGORY_PAGE_DELAY_RANGE = (0.1, 0.25)

# Hàm request với retry
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.HTTPError)),
    after=lambda retry_state: logging.warning(
        f"Thu lai that bai sau {retry_state.attempt_number} lan cho URL: {retry_state.args[0]}"
    )
)
def safe_request(url, headers):
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response

def maybe_sleep(delay_range):
    if delay_range:
        time.sleep(random.uniform(*delay_range))

# Hàm lưu và tải checkpoint
def save_checkpoint(crawled_ids, checkpoint_file):
    checkpoint_path = Path(checkpoint_file)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = checkpoint_path.with_name(f"{checkpoint_path.name}.tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(list(crawled_ids), file, ensure_ascii=False)
        file.flush()
        os.fsync(file.fileno())
    temp_path.replace(checkpoint_path)
    with open(checkpoint_path, "r+b") as file:
        os.fsync(file.fileno())

def load_checkpoint(checkpoint_file, cast=str):
    try:
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            return set()
        return {cast(item) for item in raw}
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return set()

def bootstrap_product_checkpoint(product_id_file, product_checkpoint_file):
    """
    Khoi tao product checkpoint tu product-id.txt cho cac folder du lieu cu.
    """
    product_checkpoint_path = Path(product_checkpoint_file)
    if product_checkpoint_path.exists():
        return

    product_id_path = Path(product_id_file)
    if not product_id_path.exists():
        return

    existing_ids = {
        line.strip()
        for line in product_id_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if existing_ids:
        save_checkpoint(existing_ids, product_checkpoint_file)

def _write_text_atomic(file_path, content, encoding="utf-8"):
    target_path = Path(file_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f"{target_path.name}.tmp")
    with open(temp_path, "w", encoding=encoding) as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())
    temp_path.replace(target_path)
    with open(target_path, "r+b") as file:
        os.fsync(file.fileno())

def _write_csv_atomic(file_path, dataframe, *, index=False, encoding="utf-8-sig"):
    target_path = Path(file_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f"{target_path.name}.tmp")
    dataframe.to_csv(temp_path, index=index, encoding=encoding)
    with open(temp_path, "r+b") as file:
        os.fsync(file.fileno())
    temp_path.replace(target_path)
    with open(target_path, "r+b") as file:
        os.fsync(file.fileno())

def _merge_csv_atomic(file_path, new_df, dedupe_keys, *, encoding="utf-8-sig"):
    target_path = Path(file_path)
    if target_path.exists():
        existing_df = pd.read_csv(target_path)
        merged_df = pd.concat([existing_df, new_df], ignore_index=True)
        merged_df = merged_df.drop_duplicates(subset=dedupe_keys, keep="last")
    else:
        merged_df = new_df
    _write_csv_atomic(file_path, merged_df, index=False, encoding=encoding)

def _merge_unique_lines(existing_file_path, new_lines, *, encoding="utf-8"):
    target_path = Path(existing_file_path)
    if target_path.exists():
        existing_lines = target_path.read_text(encoding=encoding).splitlines()
    else:
        existing_lines = []

    combined_lines = list(dict.fromkeys(existing_lines + list(new_lines)))
    _write_text_atomic(target_path, "\n".join(combined_lines), encoding=encoding)

def fetch_product_ids(url):
    """
    dầu vào: url là API của một danh mục sản phẩm
    dầu ra: danh sách chứa ID sản phẩm và số trang
    """
    product_list = []
    i = 1
    while True:
        logging.info(f"Crawl danh muc, trang {i}: {url.format(i)}")
        try:
            response = safe_request(url.format(i), headers=headers)
            products = json.loads(response.text)["data"]
            if not products:
                logging.info(f"Het du lieu danh mục, trang {i}")
                break
            for product in products:
                product_id = str(product["id"])
                product_list.append(product_id)
            i += 1
            maybe_sleep(CATEGORY_PAGE_DELAY_RANGE)
        except Exception as e:
            logging.error(f"Loi crawl danh muc, trang {i}: {e}")
            break
    logging.info(f"Crawl dược {len(product_list)} ID san pham")
    return product_list, i

def fetch_product_details(product_list=[]):
    """
    Lấy thông tin chi tiết sản phẩm từ Tiki API.
    """
    def fetch_one(product_id):
        logging.info(f"Crawl chi tiet san pham {product_id}")
        try:
            response = safe_request(product_url.format(product_id), headers=headers)
            return product_id, response.text
        except Exception as e:
            logging.error(f"Lỗi crawl sản phẩm {product_id} sau 3 lần thử: {e}")
            return product_id, None

    product_detail_map = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(fetch_one, product_id): product_id for product_id in product_list
        }
        for future in as_completed(future_map):
            product_id, response_text = future.result()
            if response_text is not None:
                product_detail_map[product_id] = response_text

    product_detail_list = [
        (product_id, product_detail_map[product_id])
        for product_id in product_list
        if product_id in product_detail_map
    ]
    logging.info(f"Crawl duoc {len(product_detail_list)} chi tiết san pham")
    return product_detail_list

def normalize_product_data(product):
    """
    Chuẩn hóa dữ liệu sản phẩm từ JSON.
    """
    if not product:
        return None
    try:
        e = json.loads(product)
    except json.JSONDecodeError as err:
        logging.error(f"Loi JSON: {err}")
        return None
    if not e or not e.get("id"):
        logging.warning(f"Khong tim thay 'id' trong JSON: {e}")
        return None
    
    def flatten_specifications(specifications):
        """Flatten Tiki specifications into a key-value dict."""
        flat_specs = {}
        if not isinstance(specifications, list):
            return flat_specs

        for group in specifications:
            if not isinstance(group, dict):
                continue
            attrs = group.get("attributes", [])
            if not isinstance(attrs, list):
                continue
            for attr in attrs:
                if not isinstance(attr, dict):
                    continue
                key = attr.get("code") or attr.get("name")
                if not key:
                    continue
                norm_key = str(key).strip().lower().replace(" ", "_")
                value = attr.get("value")
                if isinstance(value, dict):
                    value = value.get("name") or value.get("value")
                flat_specs[norm_key] = value
        return flat_specs

    def pick_spec(flat_specs, keys, default=None):
        for key in keys:
            if key in flat_specs and flat_specs[key] not in [None, ""]:
                return flat_specs[key]
        return default
    
    def parse_date(val):
        ts = pd.to_datetime(val, errors="coerce")
        return ts.date() if not pd.isnull(ts) else None


    soup = BeautifulSoup(e.get("description", "") or "", "html.parser")
    images = e.get("images", []) if isinstance(e.get("images", []), list) else []
    stock_item = e.get("stock_item") or {}
    specs = flatten_specifications(e.get("specifications", []))

    authors_data = e.get("authors", [])
    if isinstance(authors_data, list):
        authors = ", ".join(
            a.get("name", "") if isinstance(a, dict) else str(a)
            for a in authors_data
            if a
        ).strip() or None
    else:
        authors = None

    quantity_sold = e.get("quantity_sold")
    quantity_sold_value = None
    if isinstance(quantity_sold, dict):
        quantity_sold_value = quantity_sold.get("value")
    elif isinstance(quantity_sold, (int, float)):
        quantity_sold_value = quantity_sold

    tracking_info = e.get("tracking_info") if isinstance(e.get("tracking_info"), dict) else {}
    all_time_quantity_sold = tracking_info.get("all_time_quantity_sold", quantity_sold_value)
    current_seller = e.get("current_seller") if isinstance(e.get("current_seller"), dict) else {}
    badges_v3 = e.get("badges_v3") or []
    badge_codes = [b.get("code") for b in badges_v3 if isinstance(b, dict) and b.get("code")]

    data_product = {
        # 1) Identifiers
        "id": e["id"],
        # "sku": e.get("sku"),
        "name": e["name"],
        # "url_path": e.get("url_path") or e.get("url_key"),

        # 2) Pricing
        "price": e.get("price", e.get("list_price", e.get("original_price", None))),
        "list_price": e.get("list_price", e.get("original_price")),
        "discount_rate": e.get("discount_rate", 0),

        # 3) Social proof & sales
        "rating_average": e.get("rating_average"),
        "review_count": e.get("review_count", 0),
        "all_time_quantity_sold": e.get("all_time_quantity_sold", 0),

        # 4) Book specifications
        "authors": authors,
        "publisher_vn": pick_spec(specs, ["publisher_vn", "cong_ty_phat_hanh", "publisher"]),
        "manufacturer": pick_spec(specs, ["manufacturer", "nha_xuat_ban", "publisher"]),
        "isbn13": pick_spec(specs, ["isbn13", "isbn_13", "isbn"]),
        "book_cover": pick_spec(specs, ["book_cover", "loai_bia"]),
        "number_of_page": pick_spec(specs, ["number_of_page", "so_trang"]),
        "publication_date": parse_date(pick_spec(specs, ["publication_date", "nam_xuat_ban"])),

        # 5) Content
        # "thumbnail_url": e.get("thumbnail_url"),
        # "images": json.dumps(images, ensure_ascii=False),
        # "short_description": e.get("short_description", None),
        # "description": soup.get_text(separator=" ", strip=True),

        # 6) Merchant
        "current_seller_name": current_seller.get("name"),
        "inventory_status": e.get("inventory_status"),

        # Keep legacy image fields for compatibility.
        # "image_base_url": ", ".join(img.get("base_url", "N/A") for img in images),
        # "image_large_url": ", ".join(img.get("large_url", "N/A") for img in images),
        # "image_medium_url": ", ".join(img.get("medium_url", "N/A") for img in images),
        # "image_small_url": ", ".join(img.get("small_url", "N/A") for img in images),
        # "image_thumbnail_url": ", ".join(img.get("thumbnail_url", "N/A") for img in images),
        "stock": stock_item.get("qty", None),
        # "quantity_sold": quantity_sold_value,
        
        "has_freeship": "freeship_xtra" in badge_codes,
        "is_authentic": "is_authentic" in badge_codes,
        "has_return_policy": "return_policy" in badge_codes,
    }
    return data_product, e["id"]

def save_product_id(product_id_file, product_list=[]):
    _write_text_atomic(product_id_file, "\n".join(product_list))
    logging.info(f"Lưu file: {product_id_file}")

def save_raw_product(product_data_file, product_detail_list=[]):
    _write_text_atomic(product_data_file, "\n".join(product_detail_list), encoding="utf-8")
    logging.info(f"Lưu file: {product_data_file}")

def save_product_list_incremental(product_file, product_json):
    """
    Lưu sản phẩm tăng dần vào file CSV.
    """
    df = pd.DataFrame([product_json])
    if not Path(product_file).exists():
        df.to_csv(product_file, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(product_file, mode="a", header=False, index=False, encoding="utf-8-sig")
    logging.info(f"da them 1 san pham vào {product_file}")

def save_product_batch(product_file, product_json_list):
    """
    Ghi nhiều sản phẩm cùng lúc để giảm chi phí IO.
    """
    if not product_json_list:
        return

    df = pd.DataFrame(product_json_list)
    product_path = Path(product_file)
    if product_path.exists():
        existing_df = pd.read_csv(product_path)
        df = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset=["id"], keep="last")
    _write_csv_atomic(product_file, df, index=False, encoding="utf-8-sig")

    for _ in product_json_list:
        logging.info(f"da them 1 san pham vào {product_file}")

def load_raw_product(product_data_file):
    with open(product_data_file, "r") as file:
        return file.readlines()

# TAM THOI COMMENT CUM HAM REVIEW/CUSTOMER/BUY HISTORY
#
# def map_json_to_customers(json_data):
#     ...
#
# def map_json_to_review(json_data):
#     ...
#
# def map_json_to_buy_history(json_data):
#     ...
#
# def fetch_user_reviews_data(folder_parent_path, product_id_list):
#     ...

def fetch_and_save_product_data(folder, product_list_id):
    """
    Lấy dữ liệu chi tiết sản phẩm và lưu vào file.
    """
    product_id_file = f"./data/{folder}/product-id.txt"
    product_data_file = f"./data/{folder}/product.txt"
    product_file = f"./data/{folder}/product.csv"
    checkpoint_file = f"./data/{folder}/product_checkpoint.json"

    bootstrap_product_checkpoint(product_id_file, checkpoint_file)
    crawled_ids = load_checkpoint(checkpoint_file, cast=str)
    product_list_id = [str(pid) for pid in product_list_id if str(pid) not in crawled_ids]

    product_list = fetch_product_details(product_list_id)
    logging.info(f"Crawl duoc {len(product_list)} san pham")

    normalized_products = []
    successful_ids = []
    successful_products = []

    for requested_product_id, product in product_list:
        temp = normalize_product_data(product)
        if temp is None:
            continue

        product_json, product_id = temp
        normalized_products.append(product_json)
        successful_ids.append(str(product_id))
        successful_products.append(product)
        crawled_ids.add(str(product_id))

    logging.info(f"Co {len(product_list_id) - len(successful_ids)} loi query")

    save_product_batch(product_file, normalized_products)
    _merge_unique_lines(product_id_file, successful_ids)
    _merge_unique_lines(product_data_file, successful_products)
    save_checkpoint(crawled_ids, checkpoint_file)
    return len(successful_ids) == len(product_list_id)

def fetch_category_data(parent, data, check=False):
    """
    Thu thập dữ liệu sản phẩm từ một danh mục.
    """
    categors.append({
        "id": data.get("id", ""),
        "name": data.get("url_key", ""),
        "parent": data.get("parent_id", "")
    })
    folder_parent_path = parent if check else f"{parent}/{data['url_key'].strip()}"
    folder_path = Path(f"data/{folder_parent_path}")
    folder_path.mkdir(parents=True, exist_ok=True)
    checkpoint_file = folder_path / "checkpoint.json"

    crawled_ids = load_checkpoint(checkpoint_file)
    if str(data["id"]) in crawled_ids:
        logging.info(f"Bo qua danh muc da crawl: {folder_parent_path}")
        return True

    id_childen_list = []
    i = 1
    logging.info(f"Crawl danh muc {data['url_key']} (ID: {data['id']})")
    while True:
        try:
            response = safe_request(
                f"https://tiki.vn/api/personalish/v1/blocks/listings?limit=10&page={i}&urlKey={data['url_key']}&category={data['id']}",
                headers=headers
            )
            products = json.loads(response.text)["data"]
            if not products:
                logging.info(f"Het du lieu danh muc {data['url_key']}, trang {i}")
                break
            for product in products:
                product_id = str(product["id"])
                id_childen_list.append(product_id)
            i += 1
            maybe_sleep(CATEGORY_PAGE_DELAY_RANGE)
        except Exception as e:
            logging.error(f"Loi crawl danh muc {data['url_key']}, trang {i} sau 3 lan thu: {e}")
            break

    products_complete = fetch_and_save_product_data(folder_parent_path, id_childen_list)
    # TAM THOI BO QUA HOAN TOAN PHAN REVIEW/CUSTOMER/BUY HISTORY
    reviews_complete = True

    if products_complete and reviews_complete:
        crawled_ids.add(str(data["id"]))
        save_checkpoint(crawled_ids, checkpoint_file)
        logging.info(f"Hoan thanh danh muc {data['url_key']}")
    else:
        logging.warning(f"Danh muc {data['url_key']} chua hoan thanh, khong luu checkpoint")
        return False
    maybe_sleep(CATEGORY_PAGE_DELAY_RANGE)
    return True

def fetch_and_traverse_categories(name, category_id, parent=None):
    """
    Duyệt dệ quy các danh mục con.
    """
    checkpoint_file = f"data/{name}/checkpoint.json"
    crawled_ids = load_checkpoint(checkpoint_file)
    if str(category_id) in crawled_ids:
        logging.info(f"Bo qua danh muc da crawl: {name}")
        return True

    url = f"https://tiki.vn/api/v2/categories?include=children&parent_id={category_id}"
    try:
        response = safe_request(url, headers=headers)
        data = response.json()
    except Exception as e:
        logging.error(f"Loi crawl danh muc {name} sau 3 lan thu: {e}")
        return False

    if "data" not in data or not isinstance(data["data"], list):
        logging.warning(f"Khong tim thay danh sach danh muc con: {url}")
        return False
    categors.append({
        "id": category_id,
        "name": name,
        "parent": parent
    })
    e = data["data"]
    success = True
    if not e:
        success = fetch_category_data(name, {"url_key": name, "id": category_id}, True)
    else:
        for data in e:
            if "children" in data:
                success = fetch_and_traverse_categories(f"{name}/{data['url_key'].strip()}", data["id"], category_id) and success
            else:
                success = fetch_category_data(name, data) and success

    if success:
        crawled_ids.add(str(category_id))
        save_checkpoint(crawled_ids, checkpoint_file)
    return success

def fetch_and_save_categories(category_name, category_id, output_folder="./data"):
    """
    Thu thập danh mục sản phẩm và lưu vào file CSV.
    """
    global categors
    categors = []
    traversal_complete = fetch_and_traverse_categories(category_name, category_id)
    df = pd.DataFrame(categors)
    category_csv_path = f"{output_folder}/{category_name}/category.csv"
    _write_csv_atomic(category_csv_path, df, index=False, encoding="utf-8-sig")
    if traversal_complete:
        save_checkpoint({str(category_id)}, f"{output_folder}/{category_name}/checkpoint.json")
    logging.info(f"Luu file danh muc: {category_csv_path}")

if __name__ == "__main__":
    fetch_and_save_categories("nha-sach-tiki", "8322")
