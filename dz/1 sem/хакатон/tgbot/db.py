import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "tgbot/bot_data.db"
logger = logging.getLogger(__name__)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database tables"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_interaction TIMESTAMP
    );
    """)
    
    # Search history table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        criteria TEXT,  -- JSON string
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)
    
    # Favorites table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        listing_id TEXT,
        listing_data TEXT, -- JSON string with full listing details
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, listing_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)
    
    # Dislikes table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dislikes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        listing_id TEXT,
        listing_data TEXT, -- JSON string with full listing details
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, listing_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    # Viewed table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS viewed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        listing_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, listing_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)
    
    # Subscriptions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        criteria TEXT, -- JSON string
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# --- User Operations ---

def update_user(user_id: int, username: str = None, first_name: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO users (user_id, username, first_name, last_interaction)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        username = excluded.username,
        first_name = excluded.first_name,
        last_interaction = excluded.last_interaction
    """, (user_id, username, first_name, datetime.now()))
    conn.commit()
    conn.close()

def reset_user_data(user_id: int):
    """Delete all data for a user"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM dislikes WHERE user_id = ?", (user_id,))
    # We keep the user record itself, but clear their data
    conn.commit()
    conn.close()

# --- History Operations ---

def add_search_history(user_id: int, criteria: Dict[str, Any]):
    """Add a search to history"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Check if the exact same criteria was the last one added to avoid duplicates
    cur.execute("""
    SELECT criteria FROM search_history 
    WHERE user_id = ? 
    ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    
    criteria_json = json.dumps(criteria, ensure_ascii=False)
    
    if row and row['criteria'] == criteria_json:
        conn.close()
        return # Skip duplicate
        
    cur.execute("""
    INSERT INTO search_history (user_id, criteria)
    VALUES (?, ?)
    """, (user_id, criteria_json))
    conn.commit()
    conn.close()

def get_search_history(user_id: int, limit: int = 5) -> List[Dict]:
    """Get recent search history"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, criteria, created_at 
    FROM search_history 
    WHERE user_id = ? 
    ORDER BY created_at DESC 
    LIMIT ?
    """, (user_id, limit))
    
    history = []
    for row in cur.fetchall():
        history.append({
            'id': row['id'],
            'criteria': json.loads(row['criteria']),
            'created_at': row['created_at']
        })
    conn.close()
    return history

# --- Favorites Operations ---

def add_favorite(user_id: int, listing: Dict[str, Any]):
    conn = get_connection()
    cur = conn.cursor()
    listing_id = str(listing.get('id'))
    listing_json = json.dumps(listing, ensure_ascii=False)
    
    try:
        cur.execute("""
        INSERT INTO favorites (user_id, listing_id, listing_data)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, listing_id) DO UPDATE SET
            listing_data = excluded.listing_data,
            created_at = CURRENT_TIMESTAMP
        """, (user_id, listing_id, listing_json))
        conn.commit()
    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
    finally:
        conn.close()

def remove_favorite(user_id: int, listing_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    DELETE FROM favorites WHERE user_id = ? AND listing_id = ?
    """, (user_id, str(listing_id)))
    conn.commit()
    conn.close()

def get_favorites(user_id: int) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT listing_data FROM favorites 
    WHERE user_id = ? 
    ORDER BY created_at DESC
    """, (user_id,))
    
    favorites = []
    for row in cur.fetchall():
        favorites.append(json.loads(row['listing_data']))
    conn.close()
    return favorites

def get_favorite_ids(user_id: int) -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT listing_id FROM favorites WHERE user_id = ?", (user_id,))
    ids = [row['listing_id'] for row in cur.fetchall()]
    conn.close()
    return ids

def get_favorite_by_id(user_id: int, listing_id: str) -> Optional[Dict]:
    """Get a specific favorite listing by ID"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT listing_data FROM favorites 
    WHERE user_id = ? AND listing_id = ?
    """, (user_id, str(listing_id)))
    row = cur.fetchone()
    conn.close()
    if row:
        return json.loads(row['listing_data'])
    return None


# --- Dislikes Operations ---

def add_dislike(user_id: int, listing: Dict[str, Any], reason: str = ""):
    conn = get_connection()
    cur = conn.cursor()
    listing_id = str(listing.get('id'))
    listing_json = json.dumps(listing, ensure_ascii=False)
    
    try:
        cur.execute("""
        INSERT INTO dislikes (user_id, listing_id, listing_data, reason)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, listing_id) DO UPDATE SET
            listing_data = excluded.listing_data,
            reason = excluded.reason,
            created_at = CURRENT_TIMESTAMP
        """, (user_id, listing_id, listing_json, reason))
        conn.commit()
    except Exception as e:
        logger.error(f"Error adding dislike: {e}")
    finally:
        conn.close()

def remove_dislike(user_id: int, listing_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    DELETE FROM dislikes WHERE user_id = ? AND listing_id = ?
    """, (user_id, str(listing_id)))
    conn.commit()
    conn.close()

def get_dislikes(user_id: int) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT listing_data, reason FROM dislikes 
    WHERE user_id = ? 
    ORDER BY created_at DESC
    """, (user_id,))
    
    dislikes = []
    for row in cur.fetchall():
        data = json.loads(row['listing_data'])
        # We might want to attach the reason to the listing object or return it separately
        # For compatibility with bot.py which expects a dict of id -> data
        # But here we return a list. Let's return list of listings with reason injected if needed
        # or just the listings.
        # The bot expects: session["dislikes"][listing_id] = {"reason": "...", "listing": ...}
        # So let's return a structure that helps reconstruct that.
        dislikes.append({
            "listing": data,
            "reason": row['reason']
        })
    conn.close()
    return dislikes

def get_disliked_ids(user_id: int) -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT listing_id FROM dislikes WHERE user_id = ?", (user_id,))
    ids = [row['listing_id'] for row in cur.fetchall()]
    conn.close()
    return ids

# --- Viewed Operations ---

def add_viewed(user_id: int, listing_id: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT OR IGNORE INTO viewed (user_id, listing_id)
        VALUES (?, ?)
        """, (user_id, str(listing_id)))
        conn.commit()
    except Exception as e:
        logger.error(f"Error adding viewed: {e}")
    finally:
        conn.close()

def get_viewed_ids(user_id: int) -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT listing_id FROM viewed WHERE user_id = ?", (user_id,))
    ids = [row['listing_id'] for row in cur.fetchall()]
    conn.close()
    return ids

# --- Subscription Operations ---

def check_subscription(user_id: int, criteria: Dict[str, Any]) -> Optional[int]:
    conn = get_connection()
    cur = conn.cursor()
    criteria_json = json.dumps(criteria, ensure_ascii=False)
    
    cur.execute("SELECT id FROM subscriptions WHERE user_id = ? AND criteria = ?", (user_id, criteria_json))
    row = cur.fetchone()
    conn.close()
    if row:
        return row['id']
    return None

def add_subscription(user_id: int, criteria: Dict[str, Any]):
    conn = get_connection()
    cur = conn.cursor()
    criteria_json = json.dumps(criteria, ensure_ascii=False)
    
    # Check if already subscribed to exactly these criteria
    cur.execute("SELECT id FROM subscriptions WHERE user_id = ? AND criteria = ?", (user_id, criteria_json))
    if cur.fetchone():
        conn.close()
        return

    cur.execute("""
    INSERT INTO subscriptions (user_id, criteria)
    VALUES (?, ?)
    """, (user_id, criteria_json))
    conn.commit()
    conn.close()

def get_subscriptions(user_id: int = None) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    if user_id:
        cur.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
    else:
        cur.execute("SELECT * FROM subscriptions")
    
    subs = []
    for row in cur.fetchall():
        subs.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'criteria': json.loads(row['criteria']),
            'created_at': row['created_at']
        })
    conn.close()
    return subs

def remove_subscription(sub_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()

# --- User Info & Reset Operations ---

def get_user(user_id: int) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_last_search(user_id: int) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT criteria FROM search_history 
    WHERE user_id = ? 
    ORDER BY created_at DESC 
    LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return json.loads(row['criteria'])
    return None

def clear_user_history(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def clear_user_favorites(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def clear_user_dislikes(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM dislikes WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_active_users(hours: int = 48) -> List[int]:
    """Get users active in the last N hours"""
    conn = get_connection()
    cur = conn.cursor()
    # SQLite datetime calculation
    cur.execute(f"""
    SELECT DISTINCT user_id FROM users 
    WHERE last_interaction >= datetime('now', '-{hours} hours')
    """)
    users = [row['user_id'] for row in cur.fetchall()]
    conn.close()
    return users
