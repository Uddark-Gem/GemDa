import streamlit as st
import pandas as pd
import requests
from io import StringIO

# Page Config
st.set_page_config(page_title="Gemstone Report Dashboard", layout="wide")

# =========================
# 1. State Management & Data Loading
# =========================


# Custom CSS (Cleaned up to correct header visibility)
st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;600;700&display=swap');

        /* targeted font application */
        html, body, [class*="css"], .stApp, .stMarkdown, .stDataFrame, .stTable {
            font-family: 'Inter', sans-serif;
            font-weight: 600 !important; /* Bold everywhere as requested */
        }
        
        /* Ensure inputs and table text are also bold */
        .stTextInput input, .stNumberInput input, .stSelectbox, .stMultiSelect {
            font-weight: 600 !important;
        }

        /* 1. Logo / Title Styling */
        h1 {
            font-family: 'Outfit', sans-serif !important;
            font-weight: 700 !important;
            background: linear-gradient(90deg, #4F46E5 0%, #9333EA 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem !important;
            padding-bottom: 0.5rem;
        }

        /* 2. Modern Button Styling */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            color: white !important;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.6rem 1.2rem;
            letter-spacing: 0.02em;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(79, 70, 229, 0.2);
        }

        div.stButton > button:first-child:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(79, 70, 229, 0.3);
            background: linear-gradient(135deg, #4338ca 0%, #6D28D9 100%);
        }
        
        div.stButton > button:first-child:active {
            transform: translateY(0);
        }

        /* 3. Headers (General) */
        h2, h3 {
             font-family: 'Outfit', sans-serif !important;
             color: #1F2937;
        }

        /* --- USER REQUEST: Bold & Red Headers for Table & Sidebar Filters --- */
        
        /* Sidebar Headers (Filter Labels) */
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3, 
        section[data-testid="stSidebar"] .stMarkdown p strong {
            color: #DC2626 !important; /* Red color */
            font-weight: 700 !important;
        }

        /* Table Headers */
        [data-testid="stDataFrame"] th {
            color: #DC2626 !important; /* Red color */
            font-weight: 700 !important;
            font-size: 1rem !important;
        }
        
        /* --- USER REQUEST: Bold for Widget Labels (Display Mode, Sort By, etc.) --- */
        /* Removed forced black color to support both light and dark modes */
        label, .stWidgetLabel, .stRadio label, .stSelectbox label, p {
            font-weight: 700 !important;
        }

        /* Clean up default container padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
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
    st.title("💎 Update Gemstone Data")

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

# Load Data (with progress bar)
RAW_URL = "https://staging.gempundit.com/var/export/report.csv"

# Progress bar for loading
progress_bar = st.progress(0, text="🔄 Loading gemstone data from server...")
df_raw = load_data_from_url(RAW_URL)
progress_bar.progress(50, text="⚙️ Processing data...")

if df_raw.empty:
    progress_bar.empty()
    st.warning("No data available. Please try updating.")
    st.stop()

df_processed = process_dataframe(df_raw)
progress_bar.progress(100, text="✅ Data loaded successfully!")

# Clear progress bar after a moment
import time
time.sleep(0.5)
progress_bar.empty()

# --- Step 2: Filters (Cascading) ---
st.sidebar.image("https://cdn2.gempundit.com/skin/frontend/gempundit/default/images/logo.png", use_container_width=True)
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
    ("j_colour", "Colour"), # Added as per user request
    ("dimension_type", "Dimension Type"),
    ("product_type", "Product Type"),
    ("certification", "Certification")
]

selected_filters = {}

for col_name, label in filter_order:
    if col_name in current_df.columns:
        # Handle NaN values by filling them with "None" so they are selectable
        # We work on a temporary series to get options
        temp_series = current_df[col_name].fillna("None").astype(str)
        options = sorted(temp_series.unique())
        
        # Multiselect
        val = st.sidebar.multiselect(f"{label}", options, key=f"filter_{col_name}")
        
        if val:
            # Apply filter immediately to setup next dropdowns
            # If "None" is selected, we need to correct the filter logic to look for actual NaNs or the string "None"
            
            # Create a mask for filtering
            mask = pd.Series(False, index=current_df.index)
            
            for v in val:
                if v == "None":
                    mask |= (current_df[col_name].isna()) | (current_df[col_name] == "None")
                else:
                    mask |= (current_df[col_name] == v)
            
            current_df = current_df[mask]
            selected_filters[col_name] = val

st.sidebar.markdown("---")
st.sidebar.subheader("Range Filters")

# B. Range Filters (Sliders)
numeric_filters = [
    ("price", "Price (₹)"),
    ("carat_weight", "Carat Weight"),
    ("weight_ratti", "Weight Ratti")
]

range_selections = {}

# Helper for Sync
def update_slider(key_prefix):
    # Callback: Update from Slider to State
    val = st.session_state[f"slider_{key_prefix}"]
    st.session_state[f"min_{key_prefix}"] = val[0]
    st.session_state[f"max_{key_prefix}"] = val[1]

def update_input(key_prefix):
    # Callback: Update from Input to State
    try:
        new_min = st.session_state[f"min_{key_prefix}"]
        new_max = st.session_state[f"max_{key_prefix}"]
        
        # Validation
        if new_min > new_max:
             # If crossed, just swap or clamp? Let's clamp min to max
             new_min = new_max
             st.session_state[f"min_{key_prefix}"] = new_min
             
        st.session_state[f"slider_{key_prefix}"] = (new_min, new_max)
    except Exception:
        pass

for col, label in numeric_filters:
    if col in df_processed.columns:
        # 1. Determine Global Bounds (Data Limits)
        data_min = float(df_processed[col].min())
        data_max = float(df_processed[col].max())
        
        if data_min == data_max:
            data_min = 0.0
            data_max = max(1.0, data_max)
            
        step = 1.0 if col == "price" else 0.01
        fmt_str = "%.0f" if col == "price" else "%.2f"

        # 2. Initialize Session State if needed
        if f"min_{col}" not in st.session_state:
            st.session_state[f"min_{col}"] = data_min
        if f"max_{col}" not in st.session_state:
            st.session_state[f"max_{col}"] = data_max
        if f"slider_{col}" not in st.session_state:
            st.session_state[f"slider_{col}"] = (data_min, data_max)
            
        st.sidebar.markdown(f"**{label}**")
        
        # 3. Get current values from session state
        cur_min = st.session_state[f"min_{col}"]
        cur_max = st.session_state[f"max_{col}"]
        
        # 4. Clamp to data bounds (only if out of range)
        cur_min = max(data_min, min(cur_min, data_max))
        cur_max = max(data_min, min(cur_max, data_max))
        
        # Ensure min <= max
        if cur_min > cur_max:
            cur_min = cur_max

        # 4. Slider
        sel_range = st.sidebar.slider(
            f"Range {col}",
            min_value=data_min,
            max_value=data_max,
            value=(cur_min, cur_max),
            step=step,
            key=f"slider_{col}",
            label_visibility="collapsed",
            on_change=update_slider,
            kwargs={"key_prefix": col}
        )

        # 5. Manual Inputs
        c1, c2 = st.sidebar.columns(2)
        with c1:
            st.number_input(
                "Min",
                min_value=data_min,
                max_value=data_max,
                value=cur_min,
                step=step,
                format=fmt_str,
                key=f"min_{col}",
                label_visibility="collapsed",
                on_change=update_input,
                kwargs={"key_prefix": col}
            )
        with c2:
            st.number_input(
                "Max",
                min_value=data_min,
                max_value=data_max,
                value=cur_max,
                step=step,
                format=fmt_str,
                key=f"max_{col}",
                label_visibility="collapsed",
                on_change=update_input,
                kwargs={"key_prefix": col}
            )
            
        range_selections[col] = (cur_min, cur_max)

st.sidebar.markdown("---")

# --- Step 3: Apply Filters ---
if st.sidebar.button("Step 3: Apply Filters", type="primary", use_container_width=True):
    st.session_state["show_results"] = True
    st.session_state["current_page"] = 1  # Reset to page 1 on new filter
    st.rerun()

# =========================
# 3. Results Display
# =========================

if st.session_state["show_results"]:
    # Validation: Require specific 'gemstone' filter
    if "gemstone" not in selected_filters or not selected_filters["gemstone"]:
        st.warning("⚠ Please select a **Gemstone** to view the report.")
        st.stop()

    # Apply Range Filters to the already dropdown-filtered 'current_df'
    final_df = current_df.copy()
    
    for col, (sel_min, sel_max) in range_selections.items():
        if col in final_df.columns:
            final_df = final_df[
                (final_df[col] >= sel_min) & (final_df[col] <= sel_max)
            ]

    # --- Title ---
    st.title("💎 Filter Gemstone Data")
    
    # --- Formatting for Display (User Request: "Call for Price" if 700000) ---
    def format_price_display(val):
        try:
            if float(val) == 700000:
                return "Call for Price"
            return f"₹{val:,.0f}"
        except:
            return val

    # Apply formatting to a new column so sorting (on original 'price') still works
    final_df["display_price"] = final_df["price"].apply(format_price_display)

    # --- Metrics (Calculated on Full Data) ---
    # (Metrics currently hidden as per previous request, but available if needed)
    
    # --- Controls Layout (View Mode + Sort) ---
    c_view, c_sort_col, c_sort_order = st.columns([2, 3, 2])
    
    with c_view:
        view_mode = st.radio("Display Mode", ["Table View", "Grid View"], horizontal=True)
        
    with c_sort_col:
        sort_options = [
            "None", "price", "carat_weight", "weight_ratti", "sku", "name", 
            "gemstone", "cut", "shape"
        ]
        sort_options = [c for c in sort_options if c == "None" or c in final_df.columns]
        
        sort_by = st.selectbox("Sort Data By", sort_options, index=0)
        
    with c_sort_order:
        sort_order = st.radio("Order", ["Ascending", "Descending"], horizontal=True)

    # Apply Sorting
    if sort_by and sort_by != "None":
        ascending = (sort_order == "Ascending")
        final_df = final_df.sort_values(by=sort_by, ascending=ascending)

    # --- Column Selector (LOCKED) ---
    view_cols = [
        "sku", "name", "url_key", "treatment", "carat_weight", "weight_ratti", "display_price",
        "gemstone", "j_colour", "shape", "cut", "dimension_type", "gemstone2", "origin", 
        "product_type", "certification", "image"
    ]
    view_cols = [c for c in view_cols if c in final_df.columns]
    
    if view_mode == "Table View":
        # --- Dataframe ---
        st.dataframe(
            final_df[view_cols] if view_cols else final_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "sku": st.column_config.TextColumn("Sku"),
                "name": st.column_config.TextColumn("Name"),
                "url_key": st.column_config.LinkColumn("Product Link", display_text="Click"),
                "treatment": st.column_config.TextColumn("Treatment"),
                "carat_weight": st.column_config.NumberColumn("Carat Weight", format="%.2f"),
                "weight_ratti": st.column_config.NumberColumn("Weight Ratti", format="%.2f"),
                "display_price": st.column_config.TextColumn("Price"),
                "gemstone": st.column_config.TextColumn("Gemstone"),
                "j_colour": st.column_config.TextColumn("Colour"),
                "shape": st.column_config.TextColumn("Shape"),
                "cut": st.column_config.TextColumn("Cut"),
                "dimension_type": st.column_config.TextColumn("Dimension Type"),
                "gemstone2": st.column_config.TextColumn("Gemstone2"),
                "origin": st.column_config.TextColumn("Origin"),
                "product_type": st.column_config.TextColumn("Product Type"),
                "certification": st.column_config.TextColumn("Certification"),
                "image": st.column_config.ImageColumn("Image", help="Product Image"),
            }
        )
    else:
        # --- Grid View with Pagination ---
        
        # Pagination Settings
        ITEMS_PER_PAGE = 48
        
        # Initialize Page State
        if "current_page" not in st.session_state:
            st.session_state["current_page"] = 1
            
        # Calculate Pages
        total_items = len(final_df)
        total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        
        # Ensure current page is valid
        if st.session_state["current_page"] > total_pages:
             st.session_state["current_page"] = total_pages
        
        # Grid View Loop (Using Paginated Data)
        
        # Slice Data
        start_idx = (st.session_state["current_page"] - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        paginated_df = final_df.iloc[start_idx:end_idx]
        
        # Grid View - Row based iteration for better alignment
        # We iterate in chunks of 4 to keep rows aligned
        COLS_PER_ROW = 4
        for i in range(0, len(paginated_df), COLS_PER_ROW):
            cols = st.columns(COLS_PER_ROW)
            batch = paginated_df.iloc[i : i + COLS_PER_ROW]
            
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
                        
                        # Price Display Logic
                        # Use the pre-calculated display column or re-calculate
                        display_text = row.get('display_price', f"₹{row.get('price', 0):,.0f}")
                        
                        st.markdown(f"**{display_text}**")
                        
                        if pd.notna(row.get('url_key')):
                             st.link_button("View Product", row['url_key'])

        st.markdown("---")

        # Pagination Controls (Moved to Bottom)
        # Using vertical_alignment="center" to fix alignment issues
        c_prev, c_info, c_next = st.columns([1, 2, 1], vertical_alignment="center")
        
        with c_prev:
            if st.button("Previous", disabled=(st.session_state["current_page"] == 1), use_container_width=True):
                st.session_state["current_page"] -= 1
                st.rerun()
                
        with c_info:
            # Centered text, removed manual top padding that caused misalignment
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state['current_page']} of {total_pages} ({total_items} items)</div>", unsafe_allow_html=True)
            
        with c_next:
            if st.button("Next", disabled=(st.session_state["current_page"] == total_pages), use_container_width=True):
                st.session_state["current_page"] += 1
                st.rerun()
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
