import os
import json
from google import genai

def generate_review_summary(reviews):
    """
    Takes a list of raw reviews and uses Gemini to generate a Pros & Cons summary.
    """
    if not reviews:
        return {"pros": ["No data available"], "cons": ["No data available"]}

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    combined_reviews = "\n".join(reviews)
    
    prompt = f"""
    You are an expert e-commerce product analyst. 
    Read the following customer reviews and extract the top 2 pros and top 2 cons.
    Format your response STRICTLY as a JSON object with two keys: "pros" and "cons", 
    each containing a list of strings.
    
    Reviews:
    - {combined_reviews}
    """

    try:
        # UPGRADED TO GEMINI 3.8 FLASH
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        summary = json.loads(clean_text)
        return summary

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {"pros": ["Error fetching pros"], "cons": ["Error fetching cons"]}


def generate_spec_comparison(product_a_data, product_b_data):
    """Uses Gemini to compare specifications of two products side-by-side."""
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    data_1_str = json.dumps(product_a_data, indent=2)
    data_2_str = json.dumps(product_b_data, indent=2)
    
    prompt = f"""
    You are an expert tech reviewer and e-commerce AI. 
    Analyze the following data for two competing products.
    
    Product 1 Data: 
    {data_1_str}
    
    Product 2 Data: 
    {data_2_str}
    
    Create a detailed side-by-side specification comparison. 
    Focus on aligning similar specs (e.g., Display, Processor, RAM, Battery, Camera, Price).
    Highlight which product wins in each spec category.
    Keep the output formatted cleanly so a frontend can display it easily.
    """
    
    try:
        # UPGRADED TO GEMINI 3.8 FLASH
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Gemini Comparison Error: {e}")
        return "Comparison generation failed."