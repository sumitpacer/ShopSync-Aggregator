# ShopSync — Multi-Vendor E-Commerce Aggregator & AI Deal Advisor

ShopSync is a full-stack product search, price intelligence, and AI comparison platform built with **Python (Flask)**, **SQLite**, **Tailwind CSS**, and **Google Gemini 3.5 Flash-Lite**.

## Key Features
- **Multi-Vendor Aggregation & Caching:** Fetches, normalizes, and caches live product pricing in SQLite (`shopsync.db`) for sub-second repeat lookups.
- **90-Day Price History & "Buy Now vs. Wait" Advisor:** Tracks historical price trends with interactive Chart.js graphs and computes a deterministic deal verdict based on 90-day lows and averages.
- **10-Row AI Head-to-Head Comparison:** Generates a structured spec-by-spec comparison table and a concise Final Verdict in ₹ using Gemini 3.5 Flash-Lite.
- **Conversational AI Shopping Copilot:** Context-aware slide-over assistant that answers budget, spec, and value-for-money queries grounded in active search results.
- **Smart Filters & Persistent Wishlist:** Client-side filtering by vendor, max ₹ budget, deal verdict, and stock availability, paired with a `localStorage` wishlist tracker.

## Tech Stack
- **Backend:** Python, Flask, Flask-CORS, SQLite3, Google GenAI SDK (`gemini-3.5-flash-lite`)
- **Frontend:** HTML5, Tailwind CSS, Chart.js, Marked.js, FontAwesome



Markdown
## Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/sumitpacer/ShopSync-Aggregator.git
   cd ShopSync-Aggregator/backend
Install dependencies
Bash
pip install flask flask-cors python-dotenv google-genai requests

Configure environment variables
Create a .env file inside backend/:
Code snippet
GEMINI_API_KEY=your_gemini_api_key_here

Run the server
Bash
python app.py
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.
