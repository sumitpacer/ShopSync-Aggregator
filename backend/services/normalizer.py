def normalize_specs(raw_products):
    """
    Takes messy JSON from different vendors and normalizes it into a single, 
    clean structure for the frontend and AI to process.
    """
    normalized_list = []
    
    for item in raw_products:
        # Skip invalid data chunks
        if not isinstance(item, dict):
            continue
            
        vendor = item.get('vendor') or 'Unknown'
        
        # BUG FIX: Using 'or' bypasses None/null values perfectly.
        raw_price = item.get("product_price") or item.get("currentPrice") or item.get("price") or "Price Unavailable"
        
        # If the API returns the price as a nested dictionary (e.g., {"value": 1500, "currency": "INR"})
        if isinstance(raw_price, dict):
            raw_price = raw_price.get("value") or raw_price.get("amount") or "Price Unavailable"
            
        photo = item.get("product_photo") or item.get("imageUrl") or item.get("photo") or ""
        url = item.get("product_url") or item.get("productUrl") or item.get("offer_page_url") or "#"
        
        if vendor == 'Amazon':
            rating = item.get("product_star_rating") or "N/A"
            num_ratings = item.get("product_num_ratings") or "several"
            
            clean_product = {
                "title": item.get("product_title") or "Unknown Product",
                "raw_price": str(raw_price),
                "url": url,
                "photo": photo,
                "rating": str(rating),
                "vendor": vendor,
                "reviews": [f"This product has a rating of {rating} stars based on {num_ratings} reviews."]
            }
            normalized_list.append(clean_product)
            
        else:
            # Catch-all for Flipkart, Meesho, Myntra, etc.
            rating = item.get("product_star_rating") or item.get("rating") or "N/A"
            
            clean_product = {
                "title": item.get("product_title") or item.get("title") or "Unknown Product",
                "raw_price": str(raw_price),
                "url": url,
                "photo": photo,
                "rating": str(rating),
                "vendor": vendor,
                "reviews": [f"This product from {vendor} is rated {rating} stars."]
            }
            normalized_list.append(clean_product)
            
    return normalized_list