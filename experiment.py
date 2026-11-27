import hashlib
from database import create_tables, get_connection

def assign_variant(user_id, experiment_id="demo-experiment"):
    """Deterministically assign a user to A or B for a given experiment."""
    key = f"{experiment_id}:{user_id}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "A" if bucket < 50 else "B"

def register_user(user_id, experiment_id="demo-experiment"):
    create_tables()
    user_id = str(user_id).strip()
    if not user_id:
        raise ValueError("User ID cannot be empty.")

    variant = assign_variant(user_id, experiment_id)
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        # Keep the original assignment if this user has already been assigned.
        conn.execute("""
            INSERT OR IGNORE INTO assignments(user_id, experiment_id, variant)
            VALUES (?, ?, ?)
        """, (user_id, experiment_id, variant))
        row = conn.execute("""
            SELECT variant FROM assignments
            WHERE user_id = ? AND experiment_id = ?
        """, (user_id, experiment_id)).fetchone()
    return row[0]

def log_event(user_id, event_type, experiment_id="demo-experiment"):
    allowed = {"click", "conversion", "signup", "purchase"}
    if event_type not in allowed:
        raise ValueError(f"event_type must be one of {sorted(allowed)}")
    register_user(user_id, experiment_id)
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO events(user_id, experiment_id, event_type)
            VALUES (?, ?, ?)
        """, (str(user_id), experiment_id, event_type))
