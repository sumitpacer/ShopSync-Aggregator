import sqlite3
import hashlib
import json

DB_PATH = 'shopsync.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())

def get_query_hash(query):
    # Creates a unique ID for each search term
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

def get_cache(query):
    query_hash = get_query_hash(query)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT response_json FROM search_cache WHERE query_hash = ?", (query_hash,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
    return None

def set_cache(query, response_payload):
    query_hash = get_query_hash(query)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO search_cache (query_hash, query_text, response_json) VALUES (?, ?, ?)",
            (query_hash, query.lower().strip(), json.dumps(response_payload))
        )