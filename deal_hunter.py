import warnings
warnings.filterwarnings("ignore")

import json
import random
import google.generativeai as genai
from pydantic import BaseModel, ValidationError, ConfigDict


# =========================================================
# DATA VALIDATION MODEL (Pydantic)
# ---------------------------------------------------------
# Bu model stores.jsonl faylından oxunan datanı yoxlayır.
# Əgər JSON daxilində səhv field olsa proqram crash etməsin.
# =========================================================
class ProductData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    store: str
    product: str
    old_price: float
    new_price: float
    rating: float


# =========================================================
# GEMINI AI CONFIGURATION
# ---------------------------------------------------------
# Set GEMINI_API_KEY in environment or .env (e.g. python-dotenv).
# =========================================================
API_KEY = "AIzaSyCtFRd1hWtlYJwhqZup4w15uLyqyDq4X0Q"

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-pro")

def _safe_generate(prompt):
    """
    Call Gemini and return stripped text, or None if missing/failed.
    Prevents fallback templates when AI response exists but is malformed.
    """
    if model is None: #bu hisse AI modelin olub olmadigini yoxlayir
        return None
    try:
        response = model.generate_content(prompt)
        if response and hasattr(response, "text") and response.text:
            return response.text.strip()
    except Exception:
        pass
    return None


# =========================================================
#  DISCOUNT CALCULATION
# ---------------------------------------------------------
# Məhsulun endirim faizini hesablayır.
# =========================================================
def calculate_discount(old_price, new_price):

    discount = ((old_price - new_price) / old_price) * 100

    return discount


# =========================================================
# AI MARKETING SLOGAN
# ---------------------------------------------------------
# AI istifadə edərək məhsul üçün marketing slogan yaradır.
# Bu web app-də banner kimi istifadə olunur.
# Never returns empty: uses dynamic fallback if AI fails.
# =========================================================
def generate_marketing_slogan(product, discount):
    prompt = f"""
    Write a short exciting marketing slogan for an e-commerce promotion.

    Product: {product}
    Discount: {discount}%

    The text must be suitable for a shopping website banner.
    Maximum one sentence.
    """
    text = _safe_generate(prompt)
    if text:
        return text
    return f"🔥 {product} now available with {round(discount, 1)}% discount!"


# =========================================================
# STORE DATA LOADER
# ---------------------------------------------------------
# JSONL faylından bütün mağaza datalarını oxuyur
# və Python dictionary formatına çevirir.
# =========================================================
def load_store_data():

    stores_data = {}
    with open("data/stores.jsonl", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            try:
                validated = ProductData(**item)

            except ValidationError as e:
                print("❌ DATA ERROR:", e)
                continue

            store = validated.store
            product = validated.product

            if store not in stores_data:
                stores_data[store] = {}

            stores_data[store][product] = {
                "old_price": validated.old_price,
                "new_price": validated.new_price,
                "rating": validated.rating,
            }

    return stores_data


# =========================================================
#  FIND CHEAPEST STORE
# ---------------------------------------------------------
# Müəyyən məhsul üçün ən ucuz mağazanı tapır.
# =========================================================
def find_best_deal(product, stores_data):

    cheapest_store = None
    cheapest_price = float("inf")
    cheapest_old_price = None
    rating = None

    for store, products in stores_data.items():

        if product in products:

            data = products[product]
            price = data["new_price"]

            if price < cheapest_price:

                cheapest_price = price
                cheapest_store = store
                cheapest_old_price = data["old_price"]
                rating = data["rating"]

    return cheapest_store, cheapest_old_price, cheapest_price, rating


# =========================================================
# SUPER DEAL DETECTION
# ---------------------------------------------------------
# Əgər:
# discount >= 40%
# rating > 4
# olarsa "SUPER DEAL" hesab olunur və AI reklam yazısı yaradır.
# On AI failure, ai_marketing_text is None; UI handles fallback.
# =========================================================
def check_super_deal(product, store, old_price, new_price, rating):
    discount = calculate_discount(old_price, new_price)

    if discount >= 40 and rating > 4:
        print(f"🔥 SUPER DEAL TAPILDI → {product}")

        prompt = f"""
        Write a short catchy Instagram advertisement text
        for the product {product}.
        The product has a {round(discount, 2)}% discount.
        """
        ai_text = _safe_generate(prompt)
        if ai_text:
            print("\n🤖 AI GENERATED MARKETING TEXT:")
            print(ai_text)
            print()
        else:
            print("⚠️ AI API işləmədi – fallback UI-da göstəriləcək")

        return {
            "product": product,
            "store": store,
            "old_price": old_price,
            "new_price": new_price,
            "discount": round(discount, 2),
            "rating": rating,
            "ai_marketing_text": ai_text,
        }

    return None


# =========================================================
#  AI DEAL INSIGHT (for Streamlit UI)
# ---------------------------------------------------------
# Short explanation why the product is a good deal.
# Returns None on failure; UI layer handles fallback.
# =========================================================
def generate_ai_insight(product, discount, rating):
    prompt = f"""
    You are an e-commerce analyst.

    Explain in 2 short sentences why this product is a good deal.

    Product: {product}
    Discount: {discount}%
    Rating: {rating}

    Focus on value and savings.
    """
    return _safe_generate(prompt)


# =========================================================
#  PRICE HISTORY GENERATOR
# ---------------------------------------------------------
# Demo məqsədilə məhsulun son 6 aylıq qiymət tarixçəsini
# random şəkildə simulyasiya edir.
# =========================================================
def generate_price_history(product, current_price):

    history = []

    base_price = current_price * random.uniform(1.1, 1.4)

    for month in ["Jan","Feb","Mar","Apr","May","Jun"]:

        price = round(base_price - random.uniform(0, base_price * 0.2),2)

        history.append({
            "month": month,
            "price": price
        })

        base_price = price

    history.append({
        "month": "Now",
        "price": current_price
    })

    return history


# =========================================================
#  AI PRICE ANALYSIS (Gemini)
# ---------------------------------------------------------
# Analyzes history, predicted price, discount, rating;
# returns natural language recommendation (no predefined templates).
# =========================================================
def generate_price_analysis(product, current_price, predicted_price, discount, rating, history_list):
    """
    Send price data to Gemini; AI explains whether to buy now or wait.
    Based on price trend, predicted price, discount value, rating.
    Returns None on failure.
    """
    history_str = "\n".join(f"  {h['month']}: {h['price']} AZN" for h in (history_list or []))
    prompt = f"""You are an expert e-commerce pricing analyst.

Analyze the following product deal and price history.

Product: {product}
Current price: {current_price} AZN
Predicted next price: {predicted_price:.2f} AZN
Discount: {discount}%
Rating: {rating}

Price history:
{history_str}

Explain in 2–3 sentences whether the user should buy now or wait.

Base your reasoning on:
- price trend
- predicted price
- discount value
- rating

Do not give generic advice.
Give a professional analysis."""
    return _safe_generate(prompt)


# =========================================================
#  AI DEAL SCORE
# ---------------------------------------------------------
# Məhsulun nə qədər yaxşı deal olduğunu qiymətləndirir.
# Formula:
# discount score + rating score
# maksimum 100.
# =========================================================
def calculate_ai_deal_score(old_price, new_price, rating):

    discount = calculate_discount(old_price, new_price)

    discount_score = min(discount * 1.5, 70)

    rating_score = (rating / 5) * 30

    score = round(discount_score + rating_score)

    return min(score, 100)


# =========================================================
# PRODUCT COMPARISON
# ---------------------------------------------------------
# Bir neçə məhsulu müqayisə etmək üçün istifadə olunur.
# =========================================================
def compare_products(product_list, stores_data):

    comparison = []

    for product in product_list:

        store, old_price, new_price, rating = find_best_deal(product, stores_data)

        if store is None:
            continue

        discount = calculate_discount(old_price, new_price)

        comparison.append({
            "product": product,
            "store": store,
            "old_price": old_price,
            "new_price": new_price,
            "discount": round(discount,2),
            "rating": rating
        })

    return comparison


# =========================================================
#  MAIN PROGRAM (Terminal Version)
# ---------------------------------------------------------
# Bu hissə terminaldan işlədilən versiyadır.
# Web app ilə eyni logic istifadə olunur.
# =========================================================
if __name__ == "__main__":

    stores_data = load_store_data()

    print("Market datası yükləndi\n")

    shopping_input = input("Məhsulları vergüllə yaz: ")

    shopping_list = [p.strip().lower() for p in shopping_input.split(",")]

    print("\nAlış siyahısı:", shopping_list)

    total_price = 0
    best_plan = {}
    super_deals = []

    # =====================================================
    # DEAL ANALYSIS
    # =====================================================
    for product in shopping_list:

        store, old_price, new_price, rating = find_best_deal(product, stores_data)

        if store is None:
            print(product, "tapılmadı")
            continue

        total_price += new_price

        if store not in best_plan:
            best_plan[store] = []

        best_plan[store].append((product, new_price))

        deal = check_super_deal(product, store, old_price, new_price, rating)

        if deal:
            super_deals.append(deal)


    # =====================================================
    # BEST SHOPPING PLAN
    # =====================================================
    print("\n🛒 ƏN SƏRFƏLİ ALIŞ PLANI\n")

    for store, items in best_plan.items():

        print(store)

        for name, price in items:
            print(" ", name, "-", price, "AZN")

        print()

    print("Ümumi məbləğ:", round(total_price,2), "AZN")


    # =====================================================
    # AI DEAL SCORES
    # =====================================================
    print("\n🤖 AI DEAL SCORES\n")

    for product in shopping_list:

        store, old_price, new_price, rating = find_best_deal(product, stores_data)

        if store:

            score = calculate_ai_deal_score(old_price, new_price, rating)

            print(f"{product} → AI Deal Score: {score}/100")


    # =====================================================
    # PRICE HISTORY
    # =====================================================
    print("\n📉 PRICE HISTORY\n")

    for product in shopping_list:

        store, old_price, new_price, rating = find_best_deal(product, stores_data)

        if store:

            history = generate_price_history(product, new_price)

            print(product)

            for point in history:

                print(f"  {point['month']} → {point['price']} AZN")

            print()


    # =====================================================
    # PRODUCT COMPARISON
    # =====================================================
    print("\n⚖️ PRODUCT COMPARISON\n")

    comparison = compare_products(shopping_list, stores_data)

    for item in comparison:

        print(
            f"{item['product']} | Store: {item['store']} | "
            f"Price: {item['new_price']} AZN | "
            f"Discount: {item['discount']}% | "
            f"Rating: {item['rating']}"
        )


    # =====================================================
    # SAVE SUPER DEALS
    # =====================================================
    with open("data/best_deals.json", "w", encoding="utf-8") as f:
        json.dump(super_deals, f, indent=4, ensure_ascii=False)

    print("\nSuper deals data/best_deals.json faylına yazıldı")