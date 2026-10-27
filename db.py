"""
db.py — Database access layer
AWS Service: Amazon RDS (MySQL)
On AWS: connects to RDS MySQL via pymysql
Locally (LOCAL_DEV=1): uses SQLite for zero-setup development
All queries use parameterized statements to prevent SQL injection.
"""

import os
import datetime

_conn = None
_use_sqlite = os.environ.get("LOCAL_DEV") == "1"


def _get_conn(cfg):
    """Return a database connection, creating one if needed."""
    global _conn
    if _conn is not None:
        return _conn

    if _use_sqlite:
        import sqlite3
        _conn = sqlite3.connect(
            os.path.join(os.path.dirname(__file__), "lostfound.db"),
            check_same_thread=False,
        )
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_sqlite(_conn)
    else:
        import pymysql
        import pymysql.cursors
        _conn = pymysql.connect(
            host=cfg["db_host"],
            user=cfg["db_user"],
            password=cfg["db_password"],
            database=cfg["db_name"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            charset="utf8mb4",
        )
    return _conn


def _init_sqlite(conn):
    """Create tables in SQLite if they don't exist and run non-destructive migrations."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'LOST',
            photo_key TEXT,
            reported_by INTEGER NOT NULL,
            category TEXT DEFAULT 'General',
            location TEXT DEFAULT 'Campus Grounds',
            verification_question TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reported_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            claimed_by INTEGER NOT NULL,
            message TEXT NOT NULL,
            verification_answer TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id),
            FOREIGN KEY (claimed_by) REFERENCES users(id)
        );
    """)

    # Non-destructive migrations for existing SQLite databases
    migrations = [
        ("items", "category", "TEXT DEFAULT 'General'"),
        ("items", "location", "TEXT DEFAULT 'Campus Grounds'"),
        ("items", "verification_question", "TEXT DEFAULT ''"),
        ("claims", "verification_answer", "TEXT DEFAULT ''"),
    ]
    for table, col, col_def in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except Exception:
            # Column already exists
            pass

    conn.commit()


def _dict_from_row(row):
    """Convert a sqlite3.Row or dict to a plain dict."""
    if row is None:
        return None
    return dict(row)


def _execute(cfg, sql, params=(), fetch_one=False, fetch_all=False):
    """Execute a query, handling differences between SQLite and MySQL."""
    conn = _get_conn(cfg)
    if _use_sqlite:
        cur = conn.execute(sql.replace("%s", "?"), params)
        if fetch_one:
            row = cur.fetchone()
            return _dict_from_row(row)
        if fetch_all:
            return [_dict_from_row(r) for r in cur.fetchall()]
        conn.commit()
        return cur.lastrowid
    else:
        cur = conn.cursor()
        cur.execute(sql, params)
        if fetch_one:
            return cur.fetchone()
        if fetch_all:
            return cur.fetchall()
        conn.commit()
        return cur.lastrowid


# ── User operations ──────────────────────────────────────────────────────


def create_user(cfg, email, password_hash, role="student"):
    """Insert a new user and return their id."""
    return _execute(
        cfg,
        "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
        (email, password_hash, role),
    )


def get_user_by_email(cfg, email):
    """Look up a user by email. Returns dict or None."""
    return _execute(
        cfg,
        "SELECT id, email, password_hash, role FROM users WHERE email = %s",
        (email,),
        fetch_one=True,
    )


def get_user_by_id(cfg, user_id):
    """Look up a user by id. Returns dict or None."""
    return _execute(
        cfg,
        "SELECT id, email, password_hash, role FROM users WHERE id = %s",
        (user_id,),
        fetch_one=True,
    )


# ── Standard Campus Taxonomy ─────────────────────────────────────────────

CATEGORIES = [
    "Electronics",
    "ID & Cards",
    "Keys & Wallets",
    "Books & Stationery",
    "Bags & Backpacks",
    "Clothing & Apparel",
    "Accessories & Bottles",
    "Other",
]

LOCATIONS = [
    "Central Library",
    "Engineering Complex",
    "Science Hall",
    "Student Center & Canteen",
    "Sports & Gym Complex",
    "Main Auditorium",
    "Computer Labs",
    "Hostel / Dormitories",
    "Campus Grounds & Parking",
]


# ── Item operations ──────────────────────────────────────────────────────


def create_item(
    cfg,
    title,
    description,
    status,
    photo_key,
    reported_by,
    category="General",
    location="Campus Grounds & Parking",
    verification_question="",
):
    """Insert a new lost/found item and return its id."""
    return _execute(
        cfg,
        "INSERT INTO items (title, description, status, photo_key, reported_by, category, location, verification_question) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (title, description, status, photo_key, reported_by, category, location, verification_question),
    )


def list_items(cfg, q=None, status=None, category=None, location=None):
    """List items with optional text search, status, category, and location filters."""
    sql = "SELECT * FROM items WHERE 1=1"
    params = []

    if status and status in ("LOST", "FOUND", "CLAIMED"):
        sql += " AND status = %s"
        params.append(status)

    if category and category != "All":
        sql += " AND category = %s"
        params.append(category)

    if location and location != "All":
        sql += " AND location = %s"
        params.append(location)

    if q:
        sql += " AND (title LIKE %s OR description LIKE %s)"
        like = f"%{q}%"
        params.append(like)
        params.append(like)

    sql += " ORDER BY created_at DESC"
    return _execute(cfg, sql, tuple(params), fetch_all=True)


def get_item(cfg, item_id):
    """Get a single item by id. Returns dict or None."""
    return _execute(
        cfg,
        "SELECT * FROM items WHERE id = %s",
        (item_id,),
        fetch_one=True,
    )


def update_item_status(cfg, item_id, status):
    """Update the status of an item (e.g. to CLAIMED)."""
    _execute(
        cfg,
        "UPDATE items SET status = %s WHERE id = %s",
        (status, item_id),
    )


# ── Smart Matching Engine (USP Feature) ──────────────────────────────────


def find_smart_matches(cfg, target_item, limit=3):
    """
    Intelligent heuristic matcher: cross-matches LOST items with FOUND items.
    Calculates keyword overlap, category match, and location match to output a score (0-100%).
    """
    if not target_item:
        return []

    target_status = target_item.get("status")
    opposite_status = "FOUND" if target_status == "LOST" else "LOST"

    # Query all active items of the opposite status
    candidates = _execute(
        cfg,
        "SELECT * FROM items WHERE status = %s AND id != %s ORDER BY created_at DESC LIMIT 30",
        (opposite_status, target_item.get("id")),
        fetch_all=True,
    )

    if not candidates:
        return []

    import re

    def tokenize(text):
        if not text:
            return set()
        words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "lost", "found", "near", "this", "that",
            "have", "from", "room", "floor", "hall", "some", "item", "please"
        }
        return {w for w in words if w not in stopwords}

    target_tokens = tokenize(target_item.get("title", "") + " " + target_item.get("description", ""))
    target_category = target_item.get("category", "")
    target_location = target_item.get("location", "")

    scored_matches = []

    for cand in candidates:
        cand_tokens = tokenize(cand.get("title", "") + " " + cand.get("description", ""))
        common_words = target_tokens.intersection(cand_tokens)

        score = 0
        reasons = []

        # Keyword overlap
        if common_words:
            keyword_score = min(len(common_words) * 22, 50)
            score += keyword_score
            reasons.append(f"Matching terms: {', '.join(list(common_words)[:3])}")

        # Category match
        if target_category and cand.get("category") == target_category and target_category != "Other":
            score += 30
            reasons.append(f"Same category ({target_category})")

        # Location proximity
        if target_location and cand.get("location") == target_location:
            score += 20
            reasons.append(f"Same location ({target_location})")

        # Cap score at 98%
        final_score = min(score, 98)

        # Only suggest if there is meaningful relevance
        if final_score >= 25:
            cand_copy = dict(cand)
            cand_copy["match_score"] = final_score
            cand_copy["match_reasons"] = reasons
            scored_matches.append(cand_copy)

    scored_matches.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_matches[:limit]


# ── Claim operations ─────────────────────────────────────────────────────


def create_claim(cfg, item_id, claimed_by, message, verification_answer=""):
    """Insert a new claim on an item and return its id."""
    return _execute(
        cfg,
        "INSERT INTO claims (item_id, claimed_by, message, verification_answer) VALUES (%s, %s, %s, %s)",
        (item_id, claimed_by, message, verification_answer),
    )


def list_claims(cfg):
    """List all claims joined with item titles, claimer emails, and verification data."""
    sql = (
        "SELECT c.id, c.item_id, c.claimed_by, c.message, c.verification_answer, c.status, c.created_at, "
        "i.title AS item_title, i.category AS item_category, i.location AS item_location, "
        "i.verification_question AS item_verification_question, u.email AS claimer_email "
        "FROM claims c "
        "JOIN items i ON c.item_id = i.id "
        "JOIN users u ON c.claimed_by = u.id "
        "ORDER BY c.created_at DESC"
    )
    return _execute(cfg, sql, fetch_all=True)


def update_claim_status(cfg, claim_id, status):
    """Update a claim's status to APPROVED or REJECTED."""
    _execute(
        cfg,
        "UPDATE claims SET status = %s WHERE id = %s",
        (status, claim_id),
    )


def get_claim(cfg, claim_id):
    """Get a single claim by id."""
    return _execute(
        cfg,
        "SELECT * FROM claims WHERE id = %s",
        (claim_id,),
        fetch_one=True,
    )


def count_items(cfg):
    """Return total number of items."""
    row = _execute(cfg, "SELECT COUNT(*) AS cnt FROM items", fetch_one=True)
    return row["cnt"] if row else 0


def count_claims_pending(cfg):
    """Return number of pending claims."""
    row = _execute(
        cfg,
        "SELECT COUNT(*) AS cnt FROM claims WHERE status = 'PENDING'",
        fetch_one=True,
    )
    return row["cnt"] if row else 0


def count_items_claimed(cfg):
    """Return number of claimed items."""
    row = _execute(
        cfg,
        "SELECT COUNT(*) AS cnt FROM items WHERE status = 'CLAIMED'",
        fetch_one=True,
    )
    return row["cnt"] if row else 0
