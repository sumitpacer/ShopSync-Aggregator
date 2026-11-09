CREATE TABLE IF NOT EXISTS search_cache(
    id  INTEGER  PRIMARY KEY AUTOINCREMENT,
    query_hash text UNIQUE not null,
    query_text text NOT NULL,
    response_json text not null,
    created_at timestamp default current_timestamp

);