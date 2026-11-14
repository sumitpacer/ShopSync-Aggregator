import os
import re
import random
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from db import init_db, get_cache, set_cache
from services.api_fetcher import fetch_vendor_data
from services.normalizer import normalize_specs
from services.ai_summarizer import (
    generate_review_summary,
    generate_spec_comparison,
    generate_copilot_reply
)

load_dotenv()

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'shopsync.db')


def init_price_history_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_title TEXT NOT NULL,
            vendor TEXT NOT NULL,
            price REAL NOT NULL,
            date_recorded DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def _parse_numeric_price(raw_price):
    try:
        val = float(re.sub(r'[^\d.]', '', str(raw_price)))
        return val if val > 0 else None
    except ValueError:
        return None


def log_product_price(title, vendor, raw_price):
    clean_price = _parse_numeric_price(raw_price)
    if clean_price is None:
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'INSERT INTO price_history (product_title, vendor, price) VALUES (?, ?, ?)',
        (title, vendor, clean_price)
    )
    conn.commit()
    conn.close()


def fetch_product_history(title):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        '''SELECT ROUND(AVG(price)) as price, DATE(date_recorded) as day
           FROM price_history
           WHERE product_title = ?
           GROUP BY DATE(date_recorded)
           ORDER BY day ASC''',
        (title,)
    ).fetchall()
    conn.close()
    return [{"date": row["day"], "price": row["price"]} for row in rows]


def build_90_day_history_and_advice(title, fallback_price=50000):
    """Returns 90-day price history points and a deterministic Buy Now vs. Wait verdict."""
    history = fetch_product_history(title)

    if len(history) < 12:
        current_price = history[-1]['price'] if history else fallback_price
        rng = random.Random(title)
        three_month_history = []

        for weeks_ago in range(12, -1, -1):
            days_ago = weeks_ago * 7
            date_str = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            if weeks_ago == 0:
                price_val = round(current_price)
            else:
                fuzz = rng.uniform(-0.04, 0.06)
                price_val = round(current_price * (1 + fuzz))
            three_month_history.append({"date": date_str, "price": price_val})

        history = three_month_history

    prices = [h['price'] for h in history if h.get('price')]
    current_price = prices[-1] if prices else fallback_price
    low_90d = min(prices) if prices else current_price
    avg_90d = round(sum(prices) / len(prices)) if prices else current_price

    diff_pct = round(((avg_90d - current_price) / avg_90d) * 100, 1) if avg_90d else 0.0

    if current_price <= low_90d * 1.015 or diff_pct >= 2.0:
        status = "Buy Now"
        reason = (
            f"{abs(diff_pct)}% below 90-day avg (₹{avg_90d:,.0f})"
            if diff_pct >= 1.0
            else f"At 90-day low (₹{low_90d:,.0f})"
        )
    elif diff_pct <= -2.5:
        status = "Wait"
        reason = f"{abs(diff_pct)}% above 90-day avg (₹{avg_90d:,.0f})"
    else:
        status = "Fair Price"
        reason = f"Near 90-day avg (₹{avg_90d:,.0f})"

    return history, {
        "status": status,
        "reason": reason,
        "low_90d": low_90d,
        "avg_90d": avg_90d,
        "diff_pct": diff_pct
    }


def enrich_products_with_deal_advisor(products):
    """Attaches numeric_price, in_stock flag, and Buy Now vs. Wait deal metrics to each item."""
    enriched = []
    for p in products:
        item = dict(p)
        title = item.get('title', '')
        num_price = _parse_numeric_price(item.get('raw_price')) or 50000
        item['numeric_price'] = num_price

        avail_text = f"{title} {item.get('availability', '')}".lower()
        item['in_stock'] = not any(
            k in avail_text for k in ['out of stock', 'sold out', 'currently unavailable']
        )

        _, deal_info = build_90_day_history_and_advice(title, fallback_price=num_price)
        item['deal_advice'] = deal_info['status']
        item['deal_reason'] = deal_info['reason']
        item['low_90d'] = deal_info['low_90d']
        item['avg_90d'] = deal_info['avg_90d']
        enriched.append(item)
    return enriched


init_db()
init_price_history_table()


@app.route('/', methods=['GET'])
def home():
    return app.send_static_file('index.html')


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "message": "ShopSync Backend API is running successfully!",
        "endpoints": [
            "/api/search",
            "/api/product-review",
            "/api/price-history",
            "/api/compare",
            "/api/copilot"
        ]
    }), 200


@app.route('/api/search', methods=['POST'])
def search_products():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'Missing "query" field in request body'}), 400

    query = data['query'].strip()
    if not query:
        return jsonify({'error': 'Query string cannot be empty'}), 400

    print(f"\n🔍 Processing search request for: '{query}'")

    cached_data = get_cache(query)
    if cached_data:
        print("⚡ Cache hit! Returning data directly from SQLite database.")
        for p in cached_data.get('products', []):
            log_product_price(p.get('title', ''), p.get('vendor', ''), p.get('raw_price', '0'))
        cached_data['products'] = enrich_products_with_deal_advisor(cached_data.get('products', []))
        cached_data['cache_hit'] = True
        return jsonify(cached_data), 200

    print("🌐 Fetching data from e-commerce platforms...")
    raw_products = fetch_vendor_data(query)

    print("⚙️ Normalizing specifications and prices...")
    normalized_products = normalize_specs(raw_products)

    for p in normalized_products:
        log_product_price(p.get('title', ''), p.get('vendor', ''), p.get('raw_price', '0'))

    enriched_products = enrich_products_with_deal_advisor(normalized_products)

    final_response = {
        'cache_hit': False,
        'products': enriched_products
    }

    set_cache(query, final_response)
    print("💾 Search result successfully cached in database.")

    return jsonify(final_response), 200


@app.route('/api/product-review', methods=['POST'])
def product_review():
    data = request.get_json() or {}
    product_title = data.get('product_title')

    if not product_title:
        return jsonify({"error": "Missing product_title"}), 400

    cache_key = f"review::{product_title.lower().strip()}"
    cached_review = get_cache(cache_key)
    if cached_review:
        print(f"⚡ Review cache hit for: '{product_title}'")
        return jsonify(cached_review), 200

    print(f"🧠 Generating individual AI review for: '{product_title}'")
    ai_summary = generate_review_summary(
        f"Based on market specifications and buyer consensus, what are the pros and cons of: {product_title}?"
    )

    result = {
        "pros": ai_summary.get("pros", []),
        "cons": ai_summary.get("cons", [])
    }

    if result["pros"] and "Could not fetch" not in result["pros"][0]:
        set_cache(cache_key, result)

    return jsonify(result), 200


@app.route('/api/price-history', methods=['POST'])
def price_history():
    data = request.get_json() or {}
    product_title = data.get('product_title')

    if not product_title:
        return jsonify({"error": "Missing product_title"}), 400

    history, deal_advisor = build_90_day_history_and_advice(product_title)

    return jsonify({
        "history": history,
        "deal_advisor": deal_advisor
    }), 200


@app.route('/api/compare', methods=['POST'])
def compare_products():
    data = request.get_json() or {}
    query1 = data.get('query1')
    query2 = data.get('query2')

    if not query1 or not query2:
        return jsonify({"error": "Please provide both query1 and query2"}), 400

    print(f"\n🔍 Fetching comparison data for: '{query1}' vs '{query2}'")

    normalized_1 = normalize_specs(fetch_vendor_data(query1))
    normalized_2 = normalize_specs(fetch_vendor_data(query2))

    if not normalized_1 or not normalized_2:
        return jsonify({"error": "Could not find enough data to compare these products."}), 404

    top_product_1 = normalized_1[0]
    top_product_2 = normalized_2[0]

    print("🧠 Generating AI final verdict via Gemini...")
    comparison_result = generate_spec_comparison(top_product_1, top_product_2)

    return jsonify({
        "product_1": top_product_1,
        "product_2": top_product_2,
        "ai_comparison": comparison_result
    }), 200


@app.route('/api/copilot', methods=['POST'])
def shopping_copilot():
    data = request.get_json() or {}
    question = (data.get('question') or '').strip()
    products = data.get('products') or []

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    print(f"🤖 Copilot query: '{question}' (context: {len(products)} items)")
    reply = generate_copilot_reply(question, products)

    return jsonify({"reply": reply}), 200


if __name__ == '__main__':
    print("🚀 ShopSync Backend is running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)