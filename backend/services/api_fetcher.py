import os
import requests

def extract_price(item):
    """Exhaustively searches all possible JSON keys for a price string."""
    if not isinstance(item, dict):
        return "Price Unavailable"
        
    # 1. Check inside 'offer' dict
    offer = item.get("offer")
    if isinstance(offer, dict):
        for key in ["price", "price_raw", "price_str", "amount", "value"]:
            val = offer.get(key)
            if val and str(val).strip().lower() not in ["none", "null", "n/a", "", "price unavailable"]:
                return str(val)

    # 2. Check inside 'offers' list
    offers = item.get("offers")
    if isinstance(offers, list) and len(offers) > 0 and isinstance(offers[0], dict):
        for key in ["price", "price_raw", "price_str", "amount", "value"]:
            val = offers[0].get(key)
            if val and str(val).strip().lower() not in ["none", "null", "n/a", "", "price unavailable"]:
                return str(val)

    # 3. Check top-level item keys
    for key in ["product_price", "price", "raw_price", "price_raw", "price_str", "extracted_price"]:
        val = item.get(key)
        if val:
            if isinstance(val, dict):
                amount = val.get("value") or val.get("amount") or val.get("raw")
                if amount:
                    return f"₹{amount}" if "₹" not in str(amount) else str(amount)
            elif str(val).strip().lower() not in ["none", "null", "n/a", "", "price unavailable"]:
                return str(val)
                
    return "Price Unavailable"


def fetch_amazon(query, api_key):
    """Fetches product listings from Amazon India."""
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    querystring = {"query": query, "page": "1", "country": "IN"}
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
    }
    
    try:
        print(f"📡 Pinging Amazon API for: {query}...")
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        response.raise_for_status()
        
        products = response.json().get("data", {}).get("products", [])
        for item in products:
            item['vendor'] = 'Amazon'
            
        return products
    except Exception as e:
        print(f"🚨 Amazon Fetch Error: {e}")
        return []


def fetch_secondary_platforms(query, api_key):
    """Fetches live search results across Flipkart, Meesho, Myntra, PUMA, and other Indian stores."""
    url = "https://real-time-product-search.p.rapidapi.com/search"
    querystring = {
        "q": query,
        "country": "in",
        "language": "en",
        "limit": "10"
    }
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "real-time-product-search.p.rapidapi.com"
    }
    
    try:
        print(f"📡 Pinging Secondary E-Commerce API for: {query}...")
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        response.raise_for_status()
        
        payload = response.json().get("data", {})
        if isinstance(payload, dict):
            raw_items = payload.get("products", payload.get("organic_results", []))
        elif isinstance(payload, list):
            raw_items = payload
        else:
            raw_items = []
            
        products = []
        
        for item in raw_items:
            if not isinstance(item, dict):
                continue
                
            offer = item.get("offer") or {}
            
            # Extract store/vendor name
            store_name = offer.get("store_name") or item.get("store_name") or "Flipkart / Indian Vendor"
            
            # Extract photo URL
            photos = item.get("product_photos") or []
            if isinstance(photos, list) and len(photos) > 0:
                photo_url = photos[0]
            else:
                photo_url = item.get("product_photo") or offer.get("product_photo") or ""

            # Robust price extraction
            price = extract_price(item)

            # Extract rating & product URL
            rating = item.get("product_rating") or offer.get("product_rating") or "N/A"
            product_url = offer.get("offer_page_url") or item.get("product_page_url") or item.get("product_url") or "#"

            products.append({
                "product_title": item.get("product_title") or "Unknown Product",
                "product_price": str(price),
                "product_star_rating": str(rating),
                "product_url": product_url,
                "product_photo": photo_url,
                "vendor": store_name
            })
            
        return products
    except Exception as e:
        print(f"🚨 Secondary Vendor Fetch Error: {e}")
        return []


def fetch_vendor_data(query):
    """Aggregates search results across Amazon and secondary Indian vendors."""
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("Warning: No RAPIDAPI_KEY found in .env file.")
        return []

    all_products = []
    
    # 1. Fetch live Amazon products
    amazon_data = fetch_amazon(query, api_key)
    all_products.extend(amazon_data)
    
    # 2. Fetch live secondary vendor products
    secondary_data = fetch_secondary_platforms(query, api_key)
    all_products.extend(secondary_data)
    
    print(f"✅ Successfully aggregated {len(all_products)} total products.")
    return all_products