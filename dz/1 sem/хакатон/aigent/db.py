import sqlite3
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = "test/testdb.sqlite3"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # чтобы получать dict-подобные строки
    return conn


def init_db():
    con = get_connection()
    cur = con.cursor()

    # заявки
    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        status TEXT,
        city TEXT,
        district TEXT,
        min_area REAL,
        max_area REAL,
        min_rate REAL,
        max_rate REAL
    );
    """)

    # источники
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        base_url TEXT
    );
    """)

    # объекты
    cur.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT,
        source_id INTEGER,
        url TEXT,
        address TEXT,
        city TEXT,
        district TEXT,
        total_area REAL,
        price_total REAL,
        price_per_sqm REAL,
        floor INTEGER,
        building_type TEXT,
        year_built INTEGER,
        status TEXT,
        raw_json TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );
    """)

    # контакты
    cur.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        name TEXT,
        phone TEXT,
        email TEXT,
        messenger TEXT,
        comment TEXT,
        FOREIGN KEY (listing_id) REFERENCES listings(id)
    );
    """)

    # связь заявка <-> объект
    cur.execute("""
    CREATE TABLE IF NOT EXISTS request_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        listing_id INTEGER,
        score REAL,
        matched_filters TEXT,
        FOREIGN KEY (request_id) REFERENCES requests(id),
        FOREIGN KEY (listing_id) REFERENCES listings(id)
    );
    """)

    con.commit()
    con.close()


# ---- операции с заявками ----

def create_request(
    city: str,
    district: str,
    min_area: float,
    max_area: float,
    min_rate: float,
    max_rate: float,
) -> int:
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO requests (
            created_at, status, city, district,
            min_area, max_area, min_rate, max_rate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        "new",
        city,
        district,
        min_area,
        max_area,
        min_rate,
        max_rate,
    ))
    request_id = cur.lastrowid
    con.commit()
    con.close()
    return request_id


# ---- сохранение объявлений под заявку ----

def save_listings_for_request(
    request_id: int,
    listings: List[Dict[str, Any]],
) -> None:
    """
    Вставляет объявления в listings и создаёт связи request_listings.
    Для MVP score можно сделать простым (например, 1.0 для всех).
    """
    con = get_connection()
    cur = con.cursor()

    for item in listings:
        # источник пока пропустим, считаем source_id = NULL
        cur.execute("""
            INSERT INTO listings (
                external_id, source_id, url, address, city, district,
                total_area, price_total, price_per_sqm,
                floor, building_type, year_built,
                status, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("external_id"),
            None,
            item.get("url"),
            item["address"],
            item.get("city"),
            item.get("district"),
            item.get("total_area"),
            item.get("price_total"),
            item.get("price_per_sqm"),
            item.get("floor"),
            item.get("building_type"),
            item.get("year_built"),
            item.get("status", "active"),
            None,
        ))
        listing_id = cur.lastrowid

        cur.execute("""
            INSERT INTO request_listings (
                request_id, listing_id, score, matched_filters
            ) VALUES (?, ?, ?, ?)
        """, (
            request_id,
            listing_id,
            1.0,               # простой скоринг для MVP
            "{}",
        ))

    con.commit()
    con.close()


def get_listings_for_request(request_id: int) -> List[Dict[str, Any]]:
    """
    Возвращает список объявлений (dict) для заявки.
    """
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT
            l.*,
            s.name AS source_name
        FROM request_listings rl
        JOIN listings l ON rl.listing_id = l.id
        LEFT JOIN sources s ON l.source_id = s.id
        WHERE rl.request_id = ?
        ORDER BY rl.score DESC, l.price_per_sqm ASC
    """, (request_id,))

    rows = cur.fetchall()
    con.close()

    # rows – sqlite3.Row, приводим к обычным dict
    return [dict(r) for r in rows]
