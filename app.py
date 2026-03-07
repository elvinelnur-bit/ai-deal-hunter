"""
AI Deal Hunter - Professional E-commerce Marketplace Prototype
Streamlit app for comparing electronics deals across stores.
Integrates with deal_hunter.py: same data structure, find_best_deal, Super Deals, Gemini slogans.
"""
import html
import hashlib
import re

import pandas as pd
import plotly.express as px
import streamlit as st

# Backend: use deal_hunter when available (same data structure, find_best_deal, check_super_deal, generate_marketing_slogan)
try:
    from deal_hunter import (
        load_store_data,
        find_best_deal,
        check_super_deal,
        generate_marketing_slogan,
        model as gemini_model,
        generate_price_history,
        calculate_ai_deal_score,
        compare_products
    )
    _backend = True
except Exception:
    _backend = False
    gemini_model = None
    load_store_data = find_best_deal = check_super_deal = generate_marketing_slogan = None
    generate_price_history = calculate_ai_deal_score = compare_products = None

# =============================================================================
# CONFIG & CONSTANTS
# =============================================================================
st.set_page_config(layout="wide", page_title="AI Deal Hunter", initial_sidebar_state="expanded")

PRIMARY_COLOR = "#E30613"
PLACEHOLDER_IMG = "https://via.placeholder.com/300"

# Product image URLs (product_id -> URL). Use placeholder if missing.
PRODUCT_IMAGES = {
    "iphone_13": "images/iphone_13.jpg",
    "iphone_14": "images/iphone_14.jpeg",
    "samsung_s23": "images/Samsung_s23.jpg",

    "macbook_air_m1": "images/Macbook_Air_m1.jpg",
    "macbook_air_m2": "images/macbook_air_m2.jpeg",
    "dell_xps_13": "images/dell_xps-13.jpg",
    "hp_spectre": "images/hp_spectre.png",
    "lenovo_legion": "images/lenovo_legion.png",

    "airpods_pro": "images/airpods_pro.jpg",
    "logitech_mouse": "images/logitech_mouse.png",
    "logitech_keyboard": "images/logitech_keyboard.jpg",
    "anker_charger": "images/anker_charger.jpg",

    "apple_watch": "images/apple_watch.jpeg",
    "ipad_air": "images/ipad_air.jpg",

    "playstation5": "images/playstation_5.jpg",
    "xbox_series_x": "images/xbox_series_x.png",

    "samsung_tv_55": "images/samsung_tv_55.jpg",
    "lg_tv_55": "images/lg_tv_55.jpg",
    "ssd_1tb": "images/ssd_1tb.jpg",
    "external_hdd": "images/external_hdd.jpg",


}

CATEGORY_KEYS = ["📱 Smartphones", "💻 Laptops", "🎮 Gaming", "🎧 Audio", "📟 Tablets"]
CATEGORIES = {
    "📱 Smartphones": ["iphone_13", "iphone_14", "samsung_s23"],
    "💻 Laptops": ["macbook_air_m1", "macbook_air_m2", "dell_xps_13", "hp_spectre", "lenovo_legion"],
    "🎮 Gaming": ["playstation5", "xbox_series_x"],
    "🎧 Audio": ["airpods_pro", "logitech_mouse", "logitech_keyboard", "anker_charger"],
    "📟 Tablets": ["ipad_air", "apple_watch", "samsung_tv_55", "lg_tv_55", "ssd_1tb", "external_hdd"],
}
# Short labels for Super Deals display, e.g. "AirPods Pro (Audio)"
CATEGORY_SHORT_LABELS = {
    "📱 Smartphones": "Smartphones",
    "💻 Laptops": "Laptops",
    "🎮 Gaming": "Gaming",
    "🎧 Audio": "Audio",
    "📟 Tablets": "Tablets",
}

PRODUCT_DISPLAY_NAMES = {
    "iphone_13": "iPhone 13", "iphone_14": "iPhone 14", "samsung_s23": "Samsung S23",
    "macbook_air_m1": "MacBook Air M1", "macbook_air_m2": "MacBook Air M2",
    "airpods_pro": "AirPods Pro", "apple_watch": "Apple Watch", "ipad_air": "iPad Air",
    "playstation5": "PlayStation 5", "xbox_series_x": "Xbox Series X",
    "samsung_tv_55": "Samsung TV 55\"", "lg_tv_55": "LG TV 55\"",
    "dell_xps_13": "Dell XPS 13", "hp_spectre": "HP Spectre", "lenovo_legion": "Lenovo Legion",
    "logitech_mouse": "Logitech Mouse", "logitech_keyboard": "Logitech Keyboard",
    "anker_charger": "Anker Charger", "ssd_1tb": "SSD 1TB", "external_hdd": "External HDD",
}

STORE_DISPLAY_NAMES = {
    "KontaktHome": "Kontakt Home",
    "Irshad": "Irshad",
    "BakuElectronics": "Baku Electronics",
}


# =============================================================================
# DATA LOADING (same structure as deal_hunter.py when backend available)
# =============================================================================
def _load_stores_data_fallback():
    """Fallback when deal_hunter is not available."""
    import json
    stores_data = {}
    all_store_names = []
    with open("data/stores.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            store, product = item["store"], item["product"]
            if store not in stores_data:
                stores_data[store] = {}
                all_store_names.append(store)
            stores_data[store][product] = {
                "old_price": item["old_price"],
                "new_price": item["new_price"],
                "rating": item.get("rating", 4.5),
            }
    return stores_data, all_store_names


def get_stores_data():
    """Load product data using deal_hunter.load_store_data() when available, else fallback."""
    if _backend and load_store_data is not None:
        try:
            stores_data = load_store_data()
            all_store_names = list(stores_data.keys())
            return stores_data, all_store_names
        except Exception:
            pass
    try:
        return _load_stores_data_fallback()
    except FileNotFoundError:
        st.error("data/stores.jsonl not found.")
        st.stop()
    return {}, []


def get_cheapest_offer_for_product(product_id, stores_data, all_store_names):
    """Return (store_name, item_dict) for the store with lowest new_price. Uses find_best_deal when backend available."""
    if _backend and find_best_deal is not None:
        try:
            store, old_price, new_price, rating = find_best_deal(product_id, stores_data)
            if store is not None:
                return store, {"old_price": old_price, "new_price": new_price, "rating": rating}
        except Exception:
            pass
    best_store, best_data, best_price = None, None, None
    for store in all_store_names:
        products = stores_data.get(store, {})
        if product_id not in products:
            continue
        data = products[product_id]
        price = data["new_price"]
        if best_price is None or price < best_price:
            best_price, best_store, best_data = price, store, data
    return best_store, best_data


def get_all_offers_for_product(product_id, stores_data, all_store_names):
    """Return list of (store, new_price, item_dict) for all stores that have this product."""
    out = []
    for store in all_store_names:
        products = stores_data.get(store, {})
        if product_id not in products:
            continue
        data = products[product_id]
        out.append((store, data["new_price"], data))
    return sorted(out, key=lambda x: x[1])


def get_store_badge(store_name):
    return STORE_DISPLAY_NAMES.get(store_name, store_name)


def get_product_image_url(product_id):
    """Return image URL for product; fallback to placeholder if missing."""
    return PRODUCT_IMAGES.get(product_id, PLACEHOLDER_IMG)


def stock_indicator(product_id):
    """Deterministic 'stock left' number for UI (3-8) based on product id."""
    n = int(hashlib.md5(product_id.encode()).hexdigest()[:4], 16) % 6 + 3
    return n


def get_ai_deal_score_display(old_price, new_price, rating):
    """
    Return (score_int, color_hex) for AI Deal Score when backend available.
    score >= 90 → green, >= 75 → orange, else gray. Returns (None, None) if backend unavailable.
    """
    if not _backend or calculate_ai_deal_score is None:
        return None, None
    try:
        score = calculate_ai_deal_score(old_price, new_price, rating)
        if score >= 90:
            color = "#16a34a"
        elif score >= 75:
            color = "#ea580c"
        else:
            color = "#6b7280"
        return score, color
    except Exception:
        return None, None


def build_price_history_chart(product_id, new_price, product_name=""):
    """
    Build a Plotly line chart for price history. Returns the figure or None if backend unavailable.
    Title: 📉 Price History, X: Month, Y: Price (AZN), markers + line, color #E30613.
    """
    if not _backend or generate_price_history is None:
        return None
    try:
        history = generate_price_history(product_id, new_price)
        if not history:
            return None
        df = pd.DataFrame(history)
        fig = px.line(df, x="month", y="price", markers=True, title="📉 Price History")
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Price (AZN)",
            margin=dict(t=40, b=40),
            showlegend=False,
        )
        fig.update_traces(line_color=PRIMARY_COLOR, marker=dict(size=10, color=PRIMARY_COLOR))
        return fig
    except Exception:
        return None


def _fallback_recommendation(product, store, old_price, new_price, discount_pct, savings):
    """Simple template when AI API is unavailable."""
    store_label = get_store_badge(store)
    return (
        f"Strong deal on {product}: {discount_pct:.0f}% off saves you {savings:.0f} AZN. "
        f"Best price at {store_label} compared to typical market prices."
    )


@st.cache_data(ttl=3600)
def generate_ai_recommendation(product, store, old_price, new_price, rating):
    """
    Call Gemini to generate a short professional deal insight.
    Cached so the same deal does not trigger repeated API calls.
    On API failure, returns a simple template message.
    """
    discount = ((old_price - new_price) / old_price) * 100 if old_price else 0
    savings = old_price - new_price
    store_label = get_store_badge(store)

    prompt = f"""You are an expert e-commerce pricing analyst.

Analyze this deal and write a short professional insight explaining why it is a good deal.

Product: {product}
Store: {store_label}
Original price: {old_price} AZN
New price: {new_price} AZN
Discount: {discount:.1f}%
Rating: {rating}

Explain the value of this deal in 2-3 sentences."""

    if gemini_model is None:
        return _fallback_recommendation(product, store, old_price, new_price, discount, savings)

    try:
        response = gemini_model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass
    return _fallback_recommendation(product, store, old_price, new_price, discount, savings)


# =============================================================================
# CSS – PROFESSIONAL E-COMMERCE STYLING (high contrast, white marketplace)
# =============================================================================
def inject_css():
    # HTML/CSS must be rendered with unsafe_allow_html=True or it appears as raw text (critical for deployment)
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* === GLOBAL: white background + dark text === */
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background-color: #FFFFFF !important; }
    .block-container { padding: 0.4rem 2rem 2rem !important; max-width: 100% !important; padding-top: 0.4rem !important; background: #FFFFFF !important; }
    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; padding: 0 !important; }
    header[data-testid="stHeader"] > div { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }

    /* === Streamlit default overrides: ensure all text is visible === */
    p, span, label, div[class^="st"], .stMarkdown, .stMarkdown p { color: #111111 !important; }
    p { color: #222222 !important; }
    label { color: #111111 !important; }
    h1, h2, h3, h4, h5, h6 { color: #111111 !important; font-weight: 700 !important; }
    h1 { font-size: 2rem !important; color: #111111 !important; }
    h2 { font-size: 1.5rem !important; color: #111111 !important; }
    h3 { font-size: 1.25rem !important; color: #111111 !important; }
    h4 { font-size: 1.1rem !important; color: #111111 !important; }

    /* === Sidebar: light grey background + dark text === */
    [data-testid="stSidebar"] { background: #F5F5F5 !important; border-right: 1px solid #e0e0e0 !important; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #111111 !important; }
    [data-testid="stSidebar"] .stMarkdown { color: #111111 !important; }
    [data-testid="stSidebar"] .stMarkdown p { color: #222222 !important; }
    [data-testid="stSidebar"] .stRadio label {
        padding: 12px 14px !important; margin: 4px 8px !important; border-radius: 8px !important;
        font-weight: 500 !important; font-size: 14px !important; color: #111111 !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover { background: #fff0f0 !important; color: #E30613 !important; }
    [data-testid="stSidebar"] .stRadio label:has(input:checked) { background: #fff0f0 !important; color: #E30613 !important; }
    [data-testid="stSidebar"] .stSelectbox label { color: #111111 !important; }

    /* === Input: search and all text inputs === */
    input { color: #111111 !important; background-color: #FFFFFF !important; }
    input::placeholder { color: #666666 !important; opacity: 1; }
    [data-testid="stTextInput"] input { color: #111111 !important; background: #FFFFFF !important; border: 1px solid #ddd !important; }
    [data-testid="stTextInput"] input::placeholder { color: #666666 !important; }
    [data-testid="stTextInput"] label { color: #111111 !important; }

    /* === Tables: headers and cells visible === */
    table, th, td { color: #111111 !important; }
    th { background-color: #F5F5F5 !important; color: #111111 !important; font-weight: 600 !important; }
    td { color: #222222 !important; }
    [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td { color: #111111 !important; }

    /* === Buttons and metrics === */
    [data-testid="stMetricLabel"] { color: #111111 !important; }
    [data-testid="stMetricValue"] { color: #111111 !important; }

    /* === Header bar === */
    .header-bar {
        background: #FFFFFF !important;
        border-bottom: 2px solid #E30613;
        padding: 12px 2rem;
        margin: -0.4rem -2rem 0 -2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .header-logo { font-size: 22px; font-weight: 700; color: #E30613 !important; }
    .header-nav { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
    .header-nav span { color: #222222 !important; font-size: 13px; font-weight: 500; padding: 6px 12px; border-radius: 8px; }
    .header-nav span.active { background: #E30613 !important; color: #FFFFFF !important; }
    .basket-counter {
        background: #E30613; color: #FFFFFF !important; padding: 6px 12px; border-radius: 20px;
        font-size: 13px; font-weight: 700;
    }

    /* === Product cards: all text dark and visible === */
    .product-card {
        background: #FFFFFF !important; border-radius: 14px; padding: 0; border: 1px solid #e0e0e0;
        margin-bottom: 20px; overflow: hidden; position: relative;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .product-card:hover { border-color: #E30613; box-shadow: 0 8px 24px rgba(227,6,19,0.12); transform: translateY(-2px); }
    .product-card.selected { border: 2px solid #E30613; background: #fffbfb !important; }
    .product-card .card-img { width: 100%; height: 220px; object-fit: contain; background: #FFFFFF !important; }
    .product-card-image-wrap { border-radius: 14px 14px 0 0; overflow: hidden; border: 1px solid #e0e0e0; border-bottom: none; }
    /* Product image container: fixed height, centered, aspect ratio preserved (Streamlit DOM) */
    div[data-testid="stImage"] {
        height: 220px !important;
        background: #FFFFFF !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 20px;
        border-radius: 14px 14px 0 0;
        overflow: hidden;
    }
    div[data-testid="stImage"] img {
        max-height: 180px !important;
        max-width: 100% !important;
        width: auto !important;
        object-fit: contain !important;
    }
    .product-card-body-wrap { border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 14px 14px; padding: 0; background: #FFFFFF !important; margin-top: 0; position: relative; }
    .product-card .discount-badge {
        position: absolute; top: 10px; right: 10px; background: #E30613; color: #FFFFFF !important;
        padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; z-index: 1;
    }
    div[data-testid="column"] div[data-testid="stImage"] { border-radius: 14px 14px 0 0; overflow: hidden; border: 1px solid #e0e0e0; border-bottom: none; }
    .product-card .card-body { padding: 14px 16px; background: #FFFFFF !important; }
    .product-card .card-title { margin: 0 0 6px 0; font-size: 15px; font-weight: 600; color: #111111 !important; }
    .product-card .stars { color: #c2410c; font-size: 12px; margin: 4px 0; }
    .product-card .old-price { text-decoration: line-through; color: #555555 !important; font-size: 13px; margin: 0; }
    .product-card .new-price { color: #E30613 !important; font-size: 18px; font-weight: 700; margin: 4px 0 6px 0; }
    .product-card .store-badge {
        display: inline-block; background: #F5F5F5 !important; color: #111111 !important;
        padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; margin-bottom: 8px;
    }
    .product-card .stock { font-size: 11px; color: #E30613 !important; margin-bottom: 8px; }
    .price-table { font-size: 12px; margin-top: 8px; border-collapse: collapse; width: 100%; color: #111111 !important; }
    .price-table th, .price-table td { padding: 4px 8px; text-align: left; border-bottom: 1px solid #e0e0e0; color: #111111 !important; }
    .price-table th { color: #111111 !important; font-weight: 600 !important; background: #F5F5F5 !important; }
    .price-table td { color: #222222 !important; }

    /* === Super Deals panel (persistent, clickable) === */
    .super-deals-wrap { padding: 20px; background: #F5F5F5 !important; border-radius: 14px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .super-deals-wrap h3 { color: #E30613 !important; font-size: 16px; margin: 0 0 16px 0; font-weight: 700; }
    .super-deal-card {
        background: #FFFFFF !important; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;
        border: 1px solid #e5e7eb; font-size: 13px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        color: #111111 !important; transition: border-color 0.2s, box-shadow 0.2s;
    }
    .super-deal-card .name { font-weight: 600; color: #111111 !important; }
    .super-deal-card .new { color: #E30613 !important; font-weight: 700; }
    .super-deal-card .deal-badge { background: #E30613; color: #FFFFFF !important; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-left: 6px; }
    .super-deal-button-wrap { margin-top: 8px; margin-bottom: 4px; }
    .ai-insight-label { font-size: 10px; font-weight: 600; color: #6b7280 !important; margin-top: 10px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
    .ai-insight-box {
        font-size: 11px; color: #374151 !important; margin-top: 0; padding: 10px 12px;
        background: #e5e7eb !important; border-radius: 8px; border: none;
        line-height: 1.45; max-height: 100px; overflow-y: auto; overflow-x: hidden;
        word-wrap: break-word;
    }
    .product-card-wrapper { border-radius: 14px; border: 2px solid transparent; transition: border-color 0.2s, box-shadow 0.2s; }
    .product-card-wrapper.highlighted { border: 2px solid #E30613 !important; box-shadow: 0 0 0 2px rgba(227,6,19,0.2); }
    .product-card.highlighted, .product-card-body-wrap.highlighted { border: 2px solid #E30613 !important; box-shadow: 0 0 0 2px rgba(227,6,19,0.2); }

    /* === AI Deal of the Day banner === */
    .banner-deal-of-day {
        background: linear-gradient(90deg, #E30613 0%, #c20510 100%);
        color: #FFFFFF !important;
        padding: 20px 24px;
        border-radius: 14px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 14px rgba(227,6,19,0.3);
    }
    .banner-deal-of-day .banner-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
    .banner-deal-of-day .banner-slogan { font-size: 16px; font-weight: 500; opacity: 0.95; }

    /* === Result product cards (grid) === */
    .result-product-card {
        background: #FFFFFF !important;
        border: 1px solid #e0e0e0;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .result-product-card .old { text-decoration: line-through; color: #555555 !important; font-size: 14px; }
    .result-product-card .new { color: #E30613 !important; font-size: 20px; font-weight: 700; }
    .result-product-card .discount-badge { background: #E30613; color: white; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; display: inline-block; margin-bottom: 8px; }

    /* === Deal insights & metrics === */
    .insight-card { background: #F5F5F5 !important; border-left: 4px solid #E30613; padding: 14px 16px; border-radius: 0 10px 10px 0; margin: 12px 0; font-size: 14px; color: #111111 !important; }
    .metric-card { background: #FFFFFF !important; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; text-align: center; }
    .metric-card .value { font-size: 24px; font-weight: 700; color: #E30613 !important; }
    .metric-card .label { font-size: 12px; color: #222222 !important; margin-top: 4px; }

    /* === Caption and small text === */
    .stCaption, [data-testid="stCaptionContainer"] { color: #222222 !important; }
    small { color: #222222 !important; }

    /* === Main content: section titles and markdown === */
    [data-testid="stMarkdown"] { color: #111111 !important; }
    [data-testid="stMarkdown"] p, [data-testid="stMarkdown"] h1, [data-testid="stMarkdown"] h2,
    [data-testid="stMarkdown"] h3, [data-testid="stMarkdown"] h4 { color: #111111 !important; }
    .element-container { color: inherit; }
    div[data-testid="column"] { color: #111111 !important; }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================
if "selected_products" not in st.session_state:
    st.session_state.selected_products = set()
if "current_category" not in st.session_state:
    st.session_state.current_category = CATEGORY_KEYS[0]
if "highlight_product_id" not in st.session_state:
    st.session_state.highlight_product_id = None

# Load data once (using deal_hunter.load_store_data() when available)
stores_data, all_store_names = get_stores_data()
inject_css()


def get_category_for_product(product_id):
    """Return the category key that contains this product (for switching sidebar when Super Deal is clicked)."""
    for cat_key, pid_list in CATEGORIES.items():
        if product_id in pid_list:
            return cat_key
    return CATEGORY_KEYS[0]


# Filler phrases to strip from the start of AI responses (case-insensitive)
_AI_FILLER_PHRASES = [
    "of course.",
    "of course,",
    "sure.",
    "sure,",
    "certainly.",
    "here is the analysis:",
    "here is the professional insight:",
    "here's the analysis:",
    "here's the professional insight:",
    "here is the professional insight on the deal.",
    "here is the insight:",
    "here's the insight:",
    "here is my analysis:",
    "here's my analysis:",
]


def _strip_markdown_for_display(text):
    """Remove markdown symbols (***, ###, **, quotes) so AI insight displays as plain text."""
    if not text:
        return ""
    s = text.strip()
    # Remove markdown headings (###, ##, # at start of line or after newline)
    s = re.sub(r"^#+\s*", "", s)
    s = re.sub(r"\n#+\s*", " ", s)
    # Remove bold/italic: ***text***, **text**, *text*
    s = re.sub(r"\*{2,}([^*]*)\*{2,}", r"\1", s)
    s = re.sub(r"\*+([^*]*)\*+", r"\1", s)
    s = s.replace("***", "").replace("**", "").strip()
    # Remove surrounding quotes (single or double)
    s = s.strip().strip('"').strip("'").strip()
    return " ".join(s.split())


def _strip_filler_phrases(text):
    """Remove leading filler phrases (e.g. 'Of course.', 'Here is the analysis:') from AI text."""
    s = (text or "").strip()
    while True:
        lower = s.lower().strip()
        removed = False
        for phrase in _AI_FILLER_PHRASES:
            if lower.startswith(phrase):
                s = s[len(phrase) :].strip()
                removed = True
                break
        if not removed:
            break
    return s.strip()


def ai_insight_full_cleaned(text):
    """
    Clean full AI insight for display: remove markdown (*, #) and filler phrases.
    Returns the full text with no character or sentence limit (for scrollable container).
    """
    if not text:
        return ""
    s = _strip_markdown_for_display(text)
    s = " ".join(s.split())
    s = _strip_filler_phrases(s)
    return s


def ai_insight_preview(text, max_chars=120):
    """
    Clean AI response for short preview: remove markdown, filler phrases,
    return the first meaningful sentence about the deal, capped at max_chars.
    (Kept for any other callers that need truncated preview.)
    """
    if not text:
        return ""
    s = _strip_markdown_for_display(text)
    s = " ".join(s.split())
    s = _strip_filler_phrases(s)
    if not s:
        return ""
    # First sentence: up to first . ! ?
    for sep in ".!?":
        i = s.find(sep)
        if i != -1:
            s = s[: i + 1].strip()
            break
    if len(s) > max_chars:
        s = s[: max_chars - 1].rstrip()
        if s and s[-1] not in ".!?":
            s += "…"
    return s

# =============================================================================
# HEADER: Logo, Nav, Search, Basket Counter
# =============================================================================
def render_header(basket_count):
    active = st.session_state.current_category
    nav_html = "".join(
        f'<span class="{"active" if c == active else ""}">{c}</span>' for c in CATEGORY_KEYS
    )
    st.markdown(f"""
    <div class="header-bar">
        <div class="header-logo">🛒 AI Deal Hunter</div>
        <nav class="header-nav">{nav_html}</nav>
        <div style="display:flex;align-items:center;gap:12px;">
            <span class="basket-counter">🛒 {basket_count}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # Nav buttons (sync category with sidebar)
    cols = st.columns(5)
    for idx, cat in enumerate(CATEGORY_KEYS):
        with cols[idx]:
            if st.button(cat, key=f"nav_{idx}", use_container_width=True):
                st.session_state.current_category = cat
                st.rerun()


basket_count = len(st.session_state.selected_products)
render_header(basket_count)

# Search in main area (below header) – placeholder and label styled via CSS for visibility
search_query = st.text_input(
    "🔍 Search products",
    placeholder="Search by product name...",
    key="search",
    label_visibility="visible",
)

# =============================================================================
# SIDEBAR: Categories + Basket Preview
# =============================================================================
st.sidebar.markdown("### 📦 Categories")
category = st.sidebar.radio(
    "Category",
    CATEGORY_KEYS,
    index=CATEGORY_KEYS.index(st.session_state.current_category) if st.session_state.current_category in CATEGORY_KEYS else 0,
    label_visibility="collapsed",
)
# If user switched category, clear grid highlight so it doesn't show on wrong category
if category != st.session_state.current_category:
    st.session_state.highlight_product_id = None
st.session_state.current_category = category
products_in_category = CATEGORIES.get(category, [])

# Build full product options with rating and all store prices
product_options = []
for pid in products_in_category:
    store, data = get_cheapest_offer_for_product(pid, stores_data, all_store_names)
    if not data:
        continue
    discount = round((data["old_price"] - data["new_price"]) / data["old_price"] * 100, 0)
    name = PRODUCT_DISPLAY_NAMES.get(pid, pid)
    rating = data.get("rating", 4.5)
    all_offers = get_all_offers_for_product(pid, stores_data, all_store_names)
    product_options.append({
        "id": pid,
        "name": name,
        "old_price": data["old_price"],
        "new_price": data["new_price"],
        "discount": discount,
        "store": store,
        "rating": rating,
        "all_offers": all_offers,
    })

# Filter by search
if search_query and search_query.strip():
    q = search_query.strip().lower()
    product_options = [p for p in product_options if q in p["name"].lower()]

# Sort options
sort_by = st.sidebar.selectbox(
    "Sort by",
    ["Highest discount", "Lowest price", "Highest rating"],
    index=0,
)
if sort_by == "Highest discount":
    product_options = sorted(product_options, key=lambda x: -x["discount"])
elif sort_by == "Lowest price":
    product_options = sorted(product_options, key=lambda x: x["new_price"])
else:
    product_options = sorted(product_options, key=lambda x: -x["rating"])

# Basket preview in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛒 Basket preview")
if st.session_state.selected_products:
    for pid in sorted(st.session_state.selected_products):
        name = PRODUCT_DISPLAY_NAMES.get(pid, pid)
        st.sidebar.caption(f"• {name}")
else:
    st.sidebar.caption("_No items yet_")
st.sidebar.markdown(f"**Items:** {len(st.session_state.selected_products)}")

# =============================================================================
# SUPER DEALS: one per product (cheapest store), best per category, max 5, sorted by discount
# =============================================================================
def _build_super_deals_list(stores_data, all_store_names, max_deals=5):
    """
    Build Super Deals with no duplicates: one deal per product (cheapest store only),
    then one deal per category (highest discount in that category), sorted by discount, max 5.
    """
    # All product IDs that belong to our categories
    all_pids = set()
    for pids in CATEGORIES.values():
        all_pids.update(pids)
    # Best deal per product (cheapest store only) – one entry per product
    best_per_product = []
    for pid in all_pids:
        store, data = get_cheapest_offer_for_product(pid, stores_data, all_store_names)
        if not data:
            continue
        discount = round((data["old_price"] - data["new_price"]) / data["old_price"] * 100, 0)
        rating = data.get("rating", 4.0)
        category = get_category_for_product(pid)
        best_per_product.append({
            "product": pid,
            "name": PRODUCT_DISPLAY_NAMES.get(pid, pid),
            "store": store,
            "old_price": data["old_price"],
            "new_price": data["new_price"],
            "discount": discount,
            "rating": rating,
            "category": category,
        })
    # Best deal per category (highest discount in that category)
    best_per_category = {}
    for d in best_per_product:
        cat = d["category"]
        if cat not in best_per_category or d["discount"] > best_per_category[cat]["discount"]:
            best_per_category[cat] = d
    # Sort by discount descending, take top max_deals
    super_list = sorted(best_per_category.values(), key=lambda x: -x["discount"])[:max_deals]
    return super_list


# Flat list of all store offers (for trending and any legacy use)
_all_deals = []
for store in all_store_names:
    for pid, data in stores_data[store].items():
        discount = (data["old_price"] - data["new_price"]) / data["old_price"] * 100
        rating = data.get("rating", 4.0)
        _all_deals.append({
            "product": pid,
            "name": PRODUCT_DISPLAY_NAMES.get(pid, pid),
            "store": store,
            "old_price": data["old_price"],
            "new_price": data["new_price"],
            "discount": round(discount, 0),
            "rating": rating,
        })

_super_deals_list = _build_super_deals_list(stores_data, all_store_names, max_deals=5)

# =============================================================================
# MAIN: Product Grid (70%) + Right Panel Super Deals (30%)
# =============================================================================
main_col, right_col = st.columns([7, 3])

with main_col:
    st.markdown("#### 📋 Products")
    card_cols = st.columns(3)
    for i, opt in enumerate(product_options):
        col = card_cols[i % 3]
        with col:
            in_basket = opt["id"] in st.session_state.selected_products
            is_highlighted = st.session_state.get("highlight_product_id") == opt["id"]
            card_class = "product-card selected" if in_basket else "product-card"
            if is_highlighted:
                card_class += " highlighted"
            wrapper_class = "product-card-wrapper highlighted" if is_highlighted else "product-card-wrapper"
            store_label = get_store_badge(opt["store"])
            stock = stock_indicator(opt["id"])
            stars = "★" * int(opt["rating"]) + "☆" * (5 - int(opt["rating"]))
            img_url = get_product_image_url(opt["id"])
            # Price comparison table rows
            table_rows = "".join(
                f'<tr><td>{get_store_badge(s)}</td><td>{p} AZN</td></tr>'
                for s, p, _ in opt["all_offers"]
            )
            # AI Deal Score (when backend available)
            ai_score, ai_score_color = get_ai_deal_score_display(opt["old_price"], opt["new_price"], opt["rating"])
            ai_score_html = ""
            if ai_score is not None and ai_score_color:
                ai_score_html = f'<p class="ai-deal-score" style="font-size:12px;font-weight:600;margin:6px 0 8px 0;color:{ai_score_color} !important;">🔥 AI Deal Score: {ai_score} / 100</p>'
            # Full card wrapper (image + body) for red border when highlighted
            st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
            # Product image at top (scale to column width; fallback handled by dict + PLACEHOLDER_IMG)
            try:
                st.image(img_url)
            except Exception:
                st.image(PLACEHOLDER_IMG)
            # Card body: discount badge, name, prices, store, stock, table (must use unsafe_allow_html for HTML to render)
            product_card_html = f"""
            <div class="{card_class} product-card-body-wrap">
                <div class="discount-badge">-{int(opt["discount"])}%</div>
                <div class="card-body">
                    <h4 class="card-title">{opt["name"]}</h4>
                    <p class="stars">{stars} {opt["rating"]}</p>
                    {ai_score_html}
                    <p class="old-price">{opt["old_price"]} AZN</p>
                    <p class="new-price">{opt["new_price"]} AZN</p>
                    <span class="store-badge">{store_label}</span>
                    <p class="stock">Only {stock} left in stock!</p>
                    <table class="price-table"><thead><tr><th>Store</th><th>Price</th></tr></thead><tbody>{table_rows}</tbody></table>
                </div>
            </div>
            </div>
            """
            st.markdown(product_card_html, unsafe_allow_html=True)
            if in_basket:
                if st.button("Remove from Basket", key=f"b_{opt['id']}", use_container_width=True):
                    st.session_state.selected_products.discard(opt["id"])
                    st.rerun()
            else:
                if st.button("Add to Basket", key=f"b_{opt['id']}", use_container_width=True):
                    st.session_state.selected_products.add(opt["id"])
                    st.rerun()

    st.markdown("---")
    calculate = st.button("🔥 **Calculate Best Deals**", use_container_width=True, type="primary")

# Right panel: Super Deals (always visible; discount >= 40% and rating > 4)
with right_col:
    st.markdown("<div class='super-deals-wrap'><h3>🔥 Super Deals</h3>", unsafe_allow_html=True)
    # Each Super Deal: card HTML + clickable View button directly below (card is clickable via button)
    for d in _super_deals_list:
        ai = generate_ai_recommendation(
            d["name"], d["store"], d["old_price"], d["new_price"], d.get("rating", 4.5)
        )
        ai_full = ai_insight_full_cleaned(ai)
        category_short = CATEGORY_SHORT_LABELS.get(d["category"], d["category"])
        card_html = f"""
        <div class="super-deal-card">
            <span class="name">{html.escape(d["name"])}</span> <span style="font-size:11px;color:#6b7280;">({html.escape(category_short)})</span><br>
            <span class="new">{d["new_price"]} AZN</span> <span class="deal-badge">-{int(d["discount"])}%</span><br>
            <span style="font-size:11px;color:#666;">{html.escape(get_store_badge(d["store"]))}</span>
            <div class="ai-insight-label">AI Insight</div>
            <div class="ai-insight-box">{html.escape(ai_full)}</div>
        </div>"""
        st.markdown(card_html, unsafe_allow_html=True)
        if st.button("View → " + (d["name"][:24] + "…" if len(d["name"]) > 24 else d["name"]), key=f"super_{d['product']}_{d['store']}", use_container_width=True):
            st.session_state.highlight_product_id = d["product"]
            st.session_state.current_category = get_category_for_product(d["product"])
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Trending deals (from same global list)
    st.markdown("### 📈 Trending deals")
    trending = sorted(_all_deals, key=lambda x: -x["discount"])[:3]
    for t in trending:
        st.caption(f"**{t['name']}** — {t['new_price']} AZN (−{int(t['discount'])}%)")

# =============================================================================
# RESULTS: After "Calculate Best Deals" (uses deal_hunter: find_best_deal, check_super_deal, generate_marketing_slogan)
# =============================================================================
selected_list = sorted(st.session_state.selected_products)
if calculate and selected_list:
    results = []
    total_price = 0
    total_original = 0
    super_deal_results = []  # items that qualify as Super Deal (discount >= 40%, rating > 4)

    for product in selected_list:
        cheapest_store, best_data = get_cheapest_offer_for_product(product, stores_data, all_store_names)
        if not cheapest_store or not best_data:
            continue
        discount = (best_data["old_price"] - best_data["new_price"]) / best_data["old_price"] * 100
        total_price += best_data["new_price"]
        total_original += best_data["old_price"]
        name = PRODUCT_DISPLAY_NAMES.get(product, product)
        rating = best_data.get("rating", 4.5)
        item = {
            "product": product,
            "name": name,
            "store": cheapest_store,
            "old_price": best_data["old_price"],
            "new_price": best_data["new_price"],
            "discount": round(discount, 2),
            "rating": rating,
            "ai_marketing_text": None,
        }
        # Use backend check_super_deal to get Gemini AI marketing text when applicable
        if _backend and check_super_deal is not None:
            try:
                deal = check_super_deal(product, cheapest_store, best_data["old_price"], best_data["new_price"], rating)
                if deal and deal.get("ai_marketing_text"):
                    item["ai_marketing_text"] = deal["ai_marketing_text"]
                    super_deal_results.append(item)
            except Exception:
                if discount >= 40 and rating > 4:
                    super_deal_results.append(item)
        elif discount >= 40 and rating > 4:
            super_deal_results.append(item)
        results.append(item)

    total_savings = total_original - total_price
    best_discount = max((r["discount"] for r in results), default=0)

    st.markdown("---")
    st.markdown("## 📊 Your Best Deals")

    # Promotional banner: Deal of the Day with Gemini slogan when any Super Deal exists
    if super_deal_results and _backend and generate_marketing_slogan is not None:
        try:
            best_super = super_deal_results[0]
            slogan = generate_marketing_slogan(best_super["name"], best_super["discount"])
            if slogan:
                clean_slogan = slogan.strip().replace('"', '')
                st.markdown(f"""
                <div class="banner-deal-of-day">
                    <div class="banner-title">🔥 DEAL OF THE DAY</div>
                    <div class="banner-slogan">{html.escape(clean_slogan)}</div>
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            pass
    elif super_deal_results:
        best_super = super_deal_results[0]
        fallback_slogan = f"Limited Time Offer! {best_super['name']} now {int(best_super['discount'])}% OFF!"
        st.markdown(f"""
        <div class="banner-deal-of-day">
            <div class="banner-title">🔥 DEAL OF THE DAY</div>
            <div class="banner-slogan">{html.escape(fallback_slogan)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Product cards in 3-column grid + Price History chart under each card
    st.markdown("#### Product cards")
    card_cols = st.columns(3)
    for i, item in enumerate(results):
        with card_cols[i % 3]:
            store_label = get_store_badge(item["store"])
            ai_line = f'<p style="font-size:12px;color:#333;margin-top:8px;">{html.escape(item["ai_marketing_text"] or "")}</p>' if item.get("ai_marketing_text") else ""
            result_card_html = f"""
            <div class="result-product-card">
                <span class="discount-badge">-{item["discount"]}%</span>
                <h4 style="margin:0 0 8px 0;color:#111;">{html.escape(item["name"])}</h4>
                <p style="margin:0 0 4px 0;font-size:13px;color:#666;">{html.escape(store_label)}</p>
                <p class="old" style="margin:0;">{item["old_price"]} AZN</p>
                <p class="new" style="margin:4px 0 0 0;">{item["new_price"]} AZN</p>
                {ai_line}
            </div>
            """
            st.markdown(result_card_html, unsafe_allow_html=True)
            # Price History chart under each product card
            price_history_fig = build_price_history_chart(item["product"], item["new_price"], item["name"])
            if price_history_fig is not None:
                st.plotly_chart(price_history_fig, use_container_width=True)

    # Metrics row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Basket Price", f"{total_price:.2f} AZN", None)
    with m2:
        st.metric("Total Savings", f"{total_savings:.2f} AZN", f"vs {total_original:.2f} AZN")
    with m3:
        st.metric("Best Discount Found", f"{best_discount:.1f}%", None)

    # Price comparison bar chart (per product, stores)
    chart_data = []
    for r in results:
        for store in all_store_names:
            products = stores_data.get(store, {})
            if r["product"] in products:
                chart_data.append({
                    "Product": r["name"],
                    "Store": get_store_badge(store),
                    "Price (AZN)": products[r["product"]]["new_price"],
                })
    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        fig = px.bar(df_chart, x="Product", y="Price (AZN)", color="Store", barmode="group",
                     color_discrete_sequence=["#E30613", "#333", "#666"])
        fig.update_layout(margin=dict(t=20, b=60), xaxis_tickangle=-35, legend_title="Store")
        st.plotly_chart(fig, use_container_width=True)

    # Discount % bar chart
    df_disc = pd.DataFrame([{"Product": r["name"], "Discount %": r["discount"]} for r in results])
    fig2 = px.bar(df_disc, x="Product", y="Discount %", color="Discount %",
                  color_continuous_scale=["#ffcccc", "#E30613"], text_auto=".1f")
    fig2.update_layout(showlegend=False, margin=dict(t=20, b=60), xaxis_tickangle=-35)
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

    # Deal Insights: AI-generated recommendations (from check_super_deal when available, else generate_ai_recommendation)
    st.markdown("---")
    st.markdown("## 🔥 Deal Insights")
    for item in results:
        store_label = get_store_badge(item["store"])
        ai_insight = item.get("ai_marketing_text") or generate_ai_recommendation(
            item["name"],
            item["store"],
            item["old_price"],
            item["new_price"],
            item.get("rating", 4.5),
        )
        ai_insight_clean = _strip_markdown_for_display(ai_insight)
        st.markdown(f"""
        <div class="insight-card">
            <strong>{html.escape(item["name"])}</strong> — Best at {html.escape(store_label)} • <strong>{item["discount"]}% off</strong><br>
            {html.escape(ai_insight_clean)}
        </div>
        """, unsafe_allow_html=True)

    # Total Basket Price at bottom (st.metric)
    st.metric("Total Basket Price", f"{total_price:.2f} AZN")

    # Product Comparison table (backend: compare_products)
    if _backend and compare_products is not None:
        try:
            comparison = compare_products(selected_list, stores_data)
            if comparison:
                st.markdown("---")
                st.markdown("## 🔎 Product Comparison")
                df_comp = pd.DataFrame([
                    {
                        "Product": PRODUCT_DISPLAY_NAMES.get(row["product"], row["product"]),
                        "Best Store": get_store_badge(row["store"]),
                        "Old Price": row["old_price"],
                        "New Price": row["new_price"],
                        "Discount %": row["discount"],
                        "Rating": row["rating"],
                    }
                    for row in comparison
                ])
                st.dataframe(df_comp, use_container_width=True, hide_index=True)
        except Exception:
            pass

elif calculate and not selected_list:
    st.warning("Please add at least one product to the basket, then click **Calculate Best Deals**.")
