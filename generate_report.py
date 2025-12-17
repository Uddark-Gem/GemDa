
import pandas as pd
import requests
from io import StringIO
from tqdm import tqdm

# =========================
# 1. Download CSV via HTTP
# =========================

url = "https://staging.gempundit.com/var/export/report.csv"

# Authentication credentials
auth_http = ('pawan', 'LG65kcHz')

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/58.0.3029.110 Safari/537.3'
    )
}

response = requests.get(url, auth=auth_http, headers=headers, stream=True)

if response.status_code == 200:
    print("Downloading CSV...")

    total_size = int(response.headers.get('content-length', 0))
    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)

    with StringIO() as csv_content:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                csv_content.write(chunk.decode('utf-8'))
                progress_bar.update(len(chunk))

        progress_bar.close()
        csv_content.seek(0)

        df = pd.read_csv(csv_content)

    print("DataFrame created successfully!")
else:
    raise RuntimeError(
        f"Failed to fetch the CSV file. Status code: {response.status_code}"
    )

# =========================
# 2. Clean & Filter Data
# =========================

# Ensure these are numeric for filtering
df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
df["is_in_stock"] = pd.to_numeric(df["is_in_stock"], errors="coerce")

df_gemstone = df[
    (df["attribute_set_id"] == "Gemstones")
    & df["sku"].astype(str).str.contains("GP", na=False)
    & (df["qty"] > 0)
    & (df["is_in_stock"] == 1)
    & (~df["product_type"].fillna("").str.contains("pendant", case=False, na=False))# 1) REMOVE rows where product_type contains "pendant" (case-insensitive)
    & (df["price"] > 0)# 2) REMOVE rows where price is 0 (or missing)
].copy()

print(f"Filtered Gemstone rows: {len(df_gemstone)}")

# =========================
# 2b. Keep ONLY required columns
# =========================

columns_to_keep = [
    "sku",
    "Name",
    "url_key",
    "treatment",
    "carat_weight",
    "weight_ratti",
    "price",
    "gemstone",
    "j_colour",
    "shape",
    "cut",
    "dimension_type",
    "gemstone2",
    "origin",
    "product_type",
    "certification",
    "image",
]

existing_cols = [c for c in columns_to_keep if c in df_gemstone.columns]
df_gemstone = df_gemstone[existing_cols]

# =========================
# 2c. Format numbers, dates, URL & image
# =========================

# 1) Remove trailing .0 in numeric columns
numeric_cols = ["carat_weight", "weight_ratti", "price"]
for col in numeric_cols:
    if col in df_gemstone.columns:
        df_gemstone[col] = pd.to_numeric(df_gemstone[col], errors="coerce")
        df_gemstone[col] = df_gemstone[col].apply(
            lambda x: "" if pd.isna(x) else ("{0:g}".format(x))
        )

# 3) Prefix full URL
if "url_key" in df_gemstone.columns:
    df_gemstone["url_key"] = df_gemstone["url_key"].fillna("").astype(str)
    df_gemstone["url_key"] = (
        "https://www.gempundit.com/products/"
        + df_gemstone["url_key"].str.lstrip("/")
    )

# 4) Prefix full image URL
if "image" in df_gemstone.columns:
    df_gemstone["image"] = df_gemstone["image"].fillna("").astype(str)
    df_gemstone["image"] = (
        "https://imgcdn1.gempundit.com/media/catalog/product"
        + df_gemstone["image"].str.lstrip("/")
    )

print("Final columns used:", list(df_gemstone.columns))

# =========================
# 3. Save to CSV
# =========================
df_gemstone.to_csv('gemstone_report.csv', index=False)
print("CSV file 'gemstone_report.csv' created successfully.")

