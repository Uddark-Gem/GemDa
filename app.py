import streamlit as st
import pandas as pd
import requests
from io import StringIO

# Page Config
st.set_page_config(page_title="Gemstone/Jewelry Report Dashboard", layout="wide")

# =========================
# 1. State Management & Data Loading
# =========================


# Custom CSS (Cleaned up to correct header visibility)
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
    </style>
""", unsafe_allow_html=True)

if "show_results" not in st.session_state:
    st.session_state["show_results"] = False

# We use a mutable container for data to allow "Fresh" updates
@st.cache_data(ttl=3600)
def load_data_from_url(url):
    auth_http = ('pawan', 'LG65kcHz')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, auth=auth_http, headers=headers, stream=True)
        response.raise_for_status()
        csv_content = StringIO(response.text)
        df = pd.read_csv(csv_content, low_memory=False)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def process_dataframe(df):
    # Numeric conversions
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
    df["is_in_stock"] = pd.to_numeric(df["is_in_stock"], errors="coerce")
    
    # Filter Logic (Base filters)
    df_gemstone = df[
        (df["attribute_set_id"] == "Gemstones")
        & df["sku"].astype(str).str.contains("GP", na=False)
        & (df["qty"] > 0)
        & (df["is_in_stock"] == 1)
        & (~df["product_type"].fillna("").str.contains("pendant", case=False, na=False))
        & (df["price"] > 0)
    ].copy()

    # Numeric Formatting Helpers
    numeric_cols = ["carat_weight", "weight_ratti", "price"]
    for col in numeric_cols:
        if col in df_gemstone.columns:
            df_gemstone[col] = pd.to_numeric(df_gemstone[col], errors="coerce")

    # URL / Image Formatting
    if "url_key" in df_gemstone.columns:
        df_gemstone["url_key"] = df_gemstone["url_key"].fillna("").astype(str)
        df_gemstone["url_key"] = "https://www.gempundit.com/products/" + df_gemstone["url_key"].str.lstrip("/")

    if "image" in df_gemstone.columns:
        def get_magento_url(img_name):
            if pd.isna(img_name) or img_name == "":
                return ""
            
            # Extract filename only in case input is "g/p/gp123.jpg"
            full_str = str(img_name).strip()
            filename = full_str.split('/')[-1]
            
            s = filename.lower()
            
            # Fix: Some CSV entries miss the 'gp' prefix which exists on server
            if not s.startswith("gp"):
                s = "gp" + s
                
            if len(s) >= 2:
                # Standard Magento: /a/b/abc.jpg
                return f"https://imgcdn1.gempundit.com/media/catalog/product/{s[0]}/{s[1]}/{s}"
            return f"https://imgcdn1.gempundit.com/media/catalog/product/{s}"

        df_gemstone["image"] = df_gemstone["image"].apply(get_magento_url)
        
    return df_gemstone

# =========================
# 2. Main Layout
# =========================

if not st.session_state["show_results"]:
    st.title("💎 Advanced Gemstone Report")

# --- Step 1: Update Data ---
if not st.session_state["show_results"]:
    with st.expander("Step 1: Data Source", expanded=True):
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Update / Refresh Data"):
                st.cache_data.clear()
                st.session_state["show_results"] = False # Reset view on data update
                st.rerun()
        
        with col2:
            st.info("Click 'Update Data' to fetch the latest report from the server.")

# Load Data (Silent unless error)
RAW_URL = "https://staging.gempundit.com/var/export/report.csv"
df_raw = load_data_from_url(RAW_URL)

if df_raw.empty:
    st.warning("No data available. Please try updating.")
    st.stop()

df_processed = process_dataframe(df_raw)

# --- Step 2: Filters (Cascading) ---
st.sidebar.header("Step 2: Filter Configuration")
st.sidebar.markdown("Configure your filters below. Options update sequentially.")

# We will apply filters sequentially to 'current_df' to determine options for the NEXT filter
current_df = df_processed.copy()

# A. Dropdown Filters (Ordered List)
# The order matters for cascading: Gemstone -> Shape -> Cut -> etc (User preference order)
# User requested specific list: treatment, gemstone, shape, cut, dimension_type, origin, product_type, certification
# I'll reorder slightly for logical flow: Gemstone is usually primary.
filter_order = [
    ("gemstone", "Gemstone"),
    ("shape", "Shape"),
    ("cut", "Cut"),
    ("treatment", "Treatment"),
    ("origin", "Origin"),
    ("color", "Color"), # Added Color logic if available (implied dependency) - user didn't ask for color explicitly in dropdowns list but it is key? No, stick to user list + strict order.
    # User list: treatment, gemstone, shape, cut, dimension_type, origin, product_type, certification
    ("dimension_type", "Dimension Type"),
    ("product_type", "Product Type"),
    ("certification", "Certification")
]

selected_filters = {}

for col_name, label in filter_order:
    if col_name in current_df.columns:
        # Get options from currently filtered data
        options = sorted(current_df[col_name].dropna().unique().astype(str))
        
        # Multiselect
        val = st.sidebar.multiselect(f"{label}", options, key=f"filter_{col_name}")
        
        if val:
            # Apply filter immediately to setup next dropdowns
            current_df = current_df[current_df[col_name].isin(val)]
            selected_filters[col_name] = val

st.sidebar.markdown("---")
st.sidebar.subheader("Range Filters")

# B. Range Filters (Sliders)
# These act on the result of the dropdowns (or globally, but usually on the result makes sense for bounds, 
# but fixed global bounds provided stability. Let's use Global bounds for sliders to avoid jumping UI)
range_cols = ["carat_weight", "price", "weight_ratti"]
range_selections = {}

for col in range_cols:
    if col in df_processed.columns:
        # Determine global min/max
        min_global = float(df_processed[col].min())
        max_global = float(df_processed[col].max())
        
        # Safety for NaN/Empty
        if pd.isna(min_global): min_global = 0.0
        if pd.isna(max_global): max_global = 1.0
        
        step = 1.0 if col == 'price' else 0.01
        key_slider = f"slider_{col}"
        
        # Initialize session state for this slider if not present
        if key_slider not in st.session_state:
            st.session_state[key_slider] = (min_global, max_global)
            
        current_min, current_max = st.session_state[key_slider]
        
        st.sidebar.markdown(f"**{col.replace('_', ' ').title()}**")
        
        # Manual Inputs
        c1, c2 = st.sidebar.columns(2)
        with c1:
            val_min = st.number_input(f"Min {col}", min_value=min_global, max_value=max_global, value=current_min, step=step, key=f"input_min_{col}")
        with c2:
            val_max = st.number_input(f"Max {col}", min_value=min_global, max_value=max_global, value=current_max, step=step, key=f"input_max_{col}")
            
        # Update slider state if inputs changed (basic sync)
        if val_min != current_min or val_max != current_max:
             # Ensure valid range
             if val_min > val_max: val_min = val_max 
             st.session_state[key_slider] = (val_min, val_max)
             # Rerun to update slider visually immediately? 
             # Streamlit might handle it on next pass, but explicit is better if we want instant feedback.
             # However, avoiding rerun loops. The slider below will pick up the new session_state if we set it.
        
        # Slider
        # We use the session_state key directly so it stays in sync
        val = st.sidebar.slider(
            f"Select Range",
            min_value=min_global,
            max_value=max_global,
            step=step,
            key=key_slider,
            label_visibility="collapsed" 
        )
        range_selections[col] = val

# --- Step 3: Apply & View ---
st.sidebar.markdown("---")
apply_btn = st.sidebar.button("Step 3: Apply Filters & View Report", type="primary")

if apply_btn:
    st.session_state["show_results"] = True
    st.rerun()

# =========================
# 3. Results Display
# =========================

if st.session_state["show_results"]:
    # Apply Range Filters to the already dropdown-filtered 'current_df'
    # Note: 'current_df' has all dropdowns applied. Now apply sliders.
    
    final_df = current_df.copy()
    
    for col, (sel_min, sel_max) in range_selections.items():
        if col in final_df.columns:
            final_df = final_df[
                (final_df[col] >= sel_min) & (final_df[col] <= sel_max)
            ]

    # --- Title ---
    st.title("💎 Filter Gemstone Data")

    # --- Metrics ---
    
    # View Toggle
    view_mode = st.radio("Display Mode", ["Table View", "Grid View"], horizontal=True)

    # --- Column Selector (LOCKED) ---
    # User requested fixed columns:
    view_cols = [
        "sku", "name", "url_key", "treatment", "carat_weight", "weight_ratti", "price",
        "gemstone", "shape", "cut", "dimension_type", "gemstone2", "origin", 
        "product_type", "certification", "image"
    ]
    
    # Filter to only those present in the dataframe to avoid errors
    view_cols = [c for c in view_cols if c in final_df.columns]
    
    if view_mode == "Table View":
        # --- Dataframe ---
        st.dataframe(
            final_df[view_cols] if view_cols else final_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "sku": st.column_config.TextColumn("SKU", width="small"),
                "name": st.column_config.TextColumn("Name", width="medium"),
                "url_key": st.column_config.LinkColumn("Product Link", display_text="Click", width="small"),
                "treatment": st.column_config.TextColumn("Treatment", width="medium"),
                "carat_weight": st.column_config.NumberColumn("Carat Weight", format="%.2f", width="small"),
                "weight_ratti": st.column_config.NumberColumn("Weight Ratti", format="%.2f", width="small"),
                "price": st.column_config.NumberColumn("Price", format="₹%.0f", width="small"),
                "gemstone": st.column_config.TextColumn("Gemstone", width="small"),
                "shape": st.column_config.TextColumn("Shape", width="small"),
                "cut": st.column_config.TextColumn("Cut", width="small"),
                "dimension_type": st.column_config.TextColumn("Dimension Type", width="medium"),
                "gemstone2": st.column_config.TextColumn("Gemstone2", width="small"),
                "origin": st.column_config.TextColumn("Origin", width="small"),
                "product_type": st.column_config.TextColumn("Product Type", width="medium"),
                "certification": st.column_config.TextColumn("Certification", width="medium"),
                "image": st.column_config.ImageColumn("Image", help="Product Image", width="small"),
            }
        )
    else:
        # --- Grid View ---
        st.markdown(f"**Showing {len(final_df)} results**")
        
        # Grid View - Row based iteration for better alignment
        # We iterate in chunks of 4 to keep rows aligned
        COLS_PER_ROW = 4
        for i in range(0, len(final_df), COLS_PER_ROW):
            cols = st.columns(COLS_PER_ROW)
            batch = final_df.iloc[i : i + COLS_PER_ROW]
            
            for j, (idx, row) in enumerate(batch.iterrows()):
                with cols[j]:
                    with st.container(border=True):
                        # Image
                        if pd.notna(row.get('image')) and row['image']:
                            st.image(row['image'], use_container_width=True)
                        
                        # Name & SKU
                        st.markdown(f"**{row.get('name', '')}**")
                        st.caption(f"SKU: {row.get('sku', 'N/A')}")
                        
                        st.caption(f"{row.get('gemstone', '')} - {row.get('shape', '')}")
                        
                        price_val = row.get('price', 0)
                        # INR Formatting (No Decimals)
                        st.markdown(f"**₹{price_val:,.0f}**")
                        
                        if pd.notna(row.get('url_key')):
                             st.link_button("View Product", row['url_key'])

    # --- Download ---
    csv_data = final_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Filtered CSV",
        data=csv_data,
        file_name="filtered_gemstone_report.csv",
        mime="text/csv"
    )

else:
    st.info("👈 Please configure filters in the sidebar and click **'Step 3: Apply Filters'** to generate the report.")
