import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import database functions
from db import init_db, get_cache, set_cache

# Import custom services
from services.api_fetcher import fetch_vendor_data
from services.normalizer import normalize_specs
from services.ai_summarizer import generate_review_summary, generate_spec_comparison

load_dotenv()

app = Flask(__name__)
CORS(app) 

init_db()

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
        cached_data['cache_hit'] = True
        return jsonify(cached_data), 200

    print("🌐 Fetching data from e-commerce platforms...")
    raw_products = fetch_vendor_data(query)

    print("⚙️ Normalizing specifications and prices...")
    normalized_products = normalize_specs(raw_products)

    print("🧠 Extracting reviews and generating AI summary via Gemini...")
    all_reviews = []
    for product in normalized_products:
        all_reviews.extend(product.get('reviews', []))

    ai_summary = generate_review_summary(all_reviews)

    final_response = {
        'cache_hit': False,
        'ai_summary': ai_summary,
        'products': normalized_products
    }

    set_cache(query, final_response)
    print("💾 Search result successfully cached in database.")

    return jsonify(final_response), 200


@app.route('/api/compare', methods=['POST'])
def compare_products():
    data = request.json
    query1 = data.get('query1')
    query2 = data.get('query2')
    
    if not query1 or not query2:
        return jsonify({"error": "Please provide both query1 and query2"}), 400

    print(f"🔍 Fetching comparison data for: '{query1}' vs '{query2}'")
    
    raw_data_1 = fetch_vendor_data(query1)
    raw_data_2 = fetch_vendor_data(query2)
    
    normalized_1 = normalize_specs(raw_data_1)
    normalized_2 = normalize_specs(raw_data_2)
    
    if not normalized_1 or not normalized_2:
        return jsonify({"error": "Could not find enough data to compare these products."}), 404
        
    top_product_1 = normalized_1[0]
    top_product_2 = normalized_2[0]
    
    print("🧠 Generating AI spec comparison via Gemini...")
    comparison_result = generate_spec_comparison(top_product_1, top_product_2)
    
    return jsonify({
        "product_1": top_product_1,
        "product_2": top_product_2,
        "ai_comparison": comparison_result
    }), 200

if __name__ == '__main__':
    print("🚀 ShopSync Backend is running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)