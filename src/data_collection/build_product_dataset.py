from pathlib import Path
import argparse
import pandas as pd


def extract_category_levels(data_dir: Path, product_file: Path, max_levels: int = 5):
    """Extract cat_level_1..cat_level_n from the relative folder path."""
    rel_parent = product_file.parent.relative_to(data_dir)
    parts = list(rel_parent.parts)

    cat_values = {}
    for i in range(max_levels):
        cat_values[f"cat_level_{i + 1}"] = parts[i] if i < len(parts) else None
    return cat_values


def read_product_file(file_path: Path):
    try:
        return pd.read_csv(file_path, low_memory=False)
    except Exception as exc:
        print(f"[WARN] Cannot read {file_path}: {exc}")
        return None


def build_product_dataset(data_dir: Path, output_file: Path, dedupe: bool = True):
    product_files = sorted(data_dir.rglob("product.csv"))
    if not product_files:
        raise FileNotFoundError(f"No product.csv found under: {data_dir}")

    print(f"[INFO] Found {len(product_files)} product.csv files")

    frames = []
    for file_path in product_files:
        df = read_product_file(file_path)
        if df is None or df.empty:
            continue

        cat_info = extract_category_levels(data_dir, file_path, max_levels=5)
        for key, value in cat_info.items():
            df[key] = value
        frames.append(df)

    if not frames:
        raise ValueError("All product.csv files are empty/unreadable")

    merged = pd.concat(frames, ignore_index=True)

    # Keep one row per product id if requested.
    if dedupe and "id" in merged.columns:
        before = len(merged)
        if "review_count" in merged.columns:
            merged = merged.sort_values(by="review_count", ascending=False, na_position="last")
        merged = merged.drop_duplicates(subset=["id"], keep="first")
        after = len(merged)
        print(f"[INFO] Deduplicated by id: {before} -> {after} rows")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"[INFO] Saved dataset to: {output_file}")
    print(f"[INFO] Final shape: {merged.shape}")


def parse_args():
    parser = argparse.ArgumentParser(description="Merge all product.csv files into one product dataset")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./src/data_collection/data",
        help="Root data directory that contains category folders",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/raw/book_dataset.csv",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Keep duplicate product IDs from multiple categories",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_product_dataset(
        data_dir=Path(args.data_dir),
        output_file=Path(args.output),
        dedupe=not args.no_dedupe,
    )
