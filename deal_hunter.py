import warnings
warnings.filterwarnings("ignore")

import json
import google.generativeai as genai
from pydantic import BaseModel, ValidationError, ConfigDict


# ===============================
# PYDANTIC SCHEMA
# ===============================
class ProductData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    store: str
    product: str
    old_price: float
    new_price: float
    rating: float


# ===============================
# GEMINI API (shared with app.py)
# ===============================
API_KEY = "AIzaSyDk0_36oVduqbK9mOz_9_7Zy_sSjDH1P7Y"

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-pro")


# ===============================
# DISCOUNT FUNKSIYASI
# ===============================
def calculate_discount(old_price, new_price):

    discount = ((old_price - new_price) / old_price) * 100

    return discount


# ===============================
# AI MARKETING SLOGAN GENERATOR
# ===============================
def generate_marketing_slogan(product, discount):

    """
    Advanced Scope (UI Requirement)

    This function uses Gemini AI to generate a short marketing slogan
    for discounted products.

    The slogan will be displayed in the Streamlit web interface
    as a promotional banner above product cards.

    UI Concept:
    - Old price shown with strikethrough
    - New discounted price highlighted
    - AI-generated marketing slogan displayed at the top

    Example Output:
    "🔥 Limited Time Deal! Get the iPhone 13 now with an incredible 40% discount!"
    """

    prompt = f"""
    Write a short exciting marketing slogan for an e-commerce promotion.

    Product: {product}
    Discount: {discount}%

    The text must be suitable for a shopping website banner.
    Maximum one sentence.
    """

    try:

        response = model.generate_content(prompt)

        return response.text

    except Exception:

        return f"🔥 Special Offer! {product} now available with {discount}% discount!"


# ===============================
# DATA LOADER
# ===============================
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


# ===============================
# ƏN UCUZ MAĞAZANI TAP
# ===============================
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


# ===============================
# SUPER DEAL CHECK
# ===============================
def check_super_deal(product, store, old_price, new_price, rating):

    discount = calculate_discount(old_price, new_price)

    if discount >= 40 and rating > 4:

        print(f"🔥 SUPER DEAL TAPILDI → {product}")

        prompt = f"""
        Write a short catchy Instagram advertisement text
        for the product {product}.
        The product has a {round(discount,2)}% discount.
        """

        try:

            response = model.generate_content(prompt)

            ai_text = response.text

            # 👇 AI TEXT TERMINALDA GÖRÜNSÜN
            print("\n🤖 AI GENERATED MARKETING TEXT:")
            print(ai_text)
            print()

        except Exception as e:

            print("⚠️ AI API işləmədi:", e)

            ai_text = "Limited-time deal! Grab this product now before the discount ends!"

        return {
            "product": product,
            "store": store,
            "old_price": old_price,
            "new_price": new_price,
            "discount": round(discount,2),
            "rating": rating,
            "ai_marketing_text": ai_text
        }

    return None


# ===============================
# MAIN (terminal usage)
# ===============================
if __name__ == "__main__":

    stores_data = load_store_data()

    print("Market datası yükləndi\n")

    shopping_input = input("Məhsulları vergüllə yaz: ")

    shopping_list = [p.strip().lower() for p in shopping_input.split(",")]

    print("\nAlış siyahısı:", shopping_list)

    total_price = 0

    best_plan = {}

    super_deals = []

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

    print("\n🛒 ƏN SƏRFƏLİ ALIŞ PLANI\n")

    for store, items in best_plan.items():

        print(store)

        for name, price in items:

            print(" ", name, "-", price, "AZN")

        print()

    print("Ümumi məbləğ:", round(total_price,2), "AZN")

    with open("data/best_deals.json", "w", encoding="utf-8") as f:

        json.dump(super_deals, f, indent=4, ensure_ascii=False)

    print("\nSuper deals data/best_deals.json faylına yazıldı")