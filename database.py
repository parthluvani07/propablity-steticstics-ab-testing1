import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "database" / "ab_testing.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            variant TEXT NOT NULL CHECK (variant IN ('A', 'B')),
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            UNIQUE(user_id, experiment_id)
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_time TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_assignments_experiment
            ON assignments(experiment_id);
        CREATE INDEX IF NOT EXISTS idx_events_experiment_user
            ON events(experiment_id, user_id);
        """)

def get_summary(experiment_id):
    create_tables()
    query = """
    SELECT a.variant,
           COUNT(DISTINCT a.user_id) AS users,
           COUNT(DISTINCT CASE WHEN e.event_type = 'conversion'
                               THEN a.user_id END) AS conversions
    FROM assignments a
    LEFT JOIN events e
      ON a.user_id = e.user_id
     AND a.experiment_id = e.experiment_id
    WHERE a.experiment_id = ?
    GROUP BY a.variant
    ORDER BY a.variant
    """
    import pandas as pd
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=(experiment_id,))

def clear_experiment(experiment_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM events WHERE experiment_id = ?", (experiment_id,))
        conn.execute("DELETE FROM assignments WHERE experiment_id = ?", (experiment_id,))
        # Keep users because they may belong to other experiments.
