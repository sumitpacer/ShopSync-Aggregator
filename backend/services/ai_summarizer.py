import os
import json
from google import genai
from google.genai import types


def _get_client():
    return genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
        http_options=types.HttpOptions(timeout=15000)
    )


def generate_review_summary(reviews_or_prompt):
    """Generates a sub-second Pros & Cons JSON summary using Gemini 3.5 Flash-Lite."""
    if not reviews_or_prompt:
        return {"pros": ["No data available"], "cons": ["No data available"]}

    prompt = reviews_or_prompt[0] if isinstance(reviews_or_prompt, list) else reviews_or_prompt
    client = _get_client()

    system_instruction = (
        "You are a concise tech reviewer. Return ONLY a valid JSON object with two keys: "
        "'pros' (list of 3 short bullet strings, max 8 words each) and "
        "'cons' (list of 3 short bullet strings, max 8 words each)."
    )

    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                max_output_tokens=500,
                thinking_config=types.ThinkingConfig(thinking_level="minimal")
            )
        )

        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)

        return {
            "pros": result.get("pros", ["Strong overall performance", "Good build quality"]),
            "cons": result.get("cons", ["Premium pricing"])
        }

    except Exception as e:
        print(f"⚠️ Gemini Review Error: {e}")
        return {
            "pros": ["Could not fetch AI review right now"],
            "cons": ["Check API key or network connection"]
        }


def generate_spec_comparison(product_a_data, product_b_data):
    """Generates a 10-row minimal feature comparison and a 2-sentence final verdict."""
    client = _get_client()

    data_1_str = json.dumps(product_a_data, indent=2)
    data_2_str = json.dumps(product_b_data, indent=2)

    system_instruction = (
        "You are a concise tech buyer's advisor. Return ONLY a valid JSON object with two keys:\n"
        "1. 'rows': a list of 10 objects comparing key aspects adapted to the product category "
        "(e.g., Price, Display, Processor, RAM, Storage, Camera, Battery, Charging, Build/Weight, OS/Extras). "
        "Each object must have: 'feature' (1-2 words), 'p1' (2-4 words max for Product 1), "
        "'p2' (2-4 words max for Product 2), and 'winner' ('p1', 'p2', or 'tie').\n"
        "2. 'verdict': a crisp 2-sentence Final Verdict declaring WHICH product is the better buy and why (use ₹ for INR)."
    )

    prompt = f"Product 1:\n{data_1_str}\n\nProduct 2:\n{data_2_str}"

    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                max_output_tokens=950,
                thinking_config=types.ThinkingConfig(thinking_level="minimal")
            )
        )
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)

        return {
            "rows": result.get("rows", []),
            "verdict": result.get("verdict", "No verdict generated.")
        }

    except Exception as e:
        print(f"⚠️ Gemini Comparison Error: {e}")
        return {
            "rows": [],
            "verdict": "Comparison unavailable at the moment. Please try again."
        }


def generate_copilot_reply(user_question, products_list):
    """Answers user shopping queries grounded in the currently loaded search results."""
    client = _get_client()

    # Keep only essential fields so prompt stays fast and compact
    compact_products = [
        {
            "title": p.get("title", ""),
            "vendor": p.get("vendor", ""),
            "price": p.get("raw_price", ""),
            "deal_advice": p.get("deal_advice", "")
        }
        for p in (products_list or [])[:12]
    ]

    system_instruction = (
        "You are ShopSync AI Copilot, a sharp, concise shopping assistant for Indian buyers. "
        "Answer the user's question using the provided product list (and general spec knowledge if needed). "
        "Keep responses under 80 words, use crisp bullet points or bold product names, and quote prices in ₹."
    )

    context_block = (
        f"Loaded Products:\n{json.dumps(compact_products, indent=2)}"
        if compact_products
        else "No products searched yet on screen."
    )
    prompt = f"{context_block}\n\nUser Question: {user_question}"

    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=350,
                thinking_config=types.ThinkingConfig(thinking_level="minimal")
            )
        )
        return response.text.strip()

    except Exception as e:
        print(f"⚠️ Gemini Copilot Error: {e}")
        return "Sorry, I couldn't process that right now. Please try again in a moment."