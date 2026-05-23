import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join("data", "smart_order_feedback.db")

def get_connection():
    """Returns a connection to the SQLite database. Ensures directories exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def _migrate_order_log(cursor):
    cols = {row[1] for row in cursor.execute("PRAGMA table_info(order_recommendation_log)")}
    for name, typedef in [
        ("workflow_status", "TEXT DEFAULT 'CONFIRMED'"),
        ("adjust_reason_code", "TEXT"),
        ("adjust_reason_note", "TEXT"),
        ("sns_uplift_applied", "REAL DEFAULT 0"),
        ("event_uplift_applied", "REAL DEFAULT 0"),
    ]:
        if name not in cols:
            cursor.execute(
                f"ALTER TABLE order_recommendation_log ADD COLUMN {name} {typedef}"
            )


def _create_external_signal_log(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS external_signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL,
            store_id TEXT NOT NULL,
            signal_type TEXT NOT NULL DEFAULT 'combined',
            payload_json TEXT NOT NULL,
            total_sns_uplift REAL DEFAULT 0,
            total_event_uplift REAL DEFAULT 0
        )
    """)


def init_db():
    """Initializes the feedback SQLite database and tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_recommendation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL,
            store_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            predicted_sales_qty REAL NOT NULL,
            safety_stock INTEGER NOT NULL,
            current_stock INTEGER NOT NULL,
            recommended_order_qty INTEGER NOT NULL,
            owner_adjusted_qty INTEGER NOT NULL,
            is_submitted INTEGER NOT NULL DEFAULT 1
        )
    """)
    _migrate_order_log(cursor)
    _create_external_signal_log(cursor)
    conn.commit()
    conn.close()
    print("Database initialized successfully at:", DB_PATH)

def save_recommendation_feedback(
    date_str,
    store_id,
    product_id,
    predicted_sales,
    safety_stock,
    current_stock,
    recommended_order,
    adjusted_order,
    workflow_status="CONFIRMED",
    adjust_reason_code=None,
    adjust_reason_note=None,
    sns_uplift=0.0,
    event_uplift=0.0,
):
    """
    Saves or updates a recommendation confirmation in the feedback log.
    If a record exists for the same date, store, and product, it will overwrite it.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if a log entry already exists for this specific combination
    cursor.execute("""
        SELECT id FROM order_recommendation_log 
        WHERE date = ? AND store_id = ? AND product_id = ?
    """, (date_str, store_id, product_id))
    
    existing = cursor.fetchone()
    
    if existing:
        # Update existing record
        cursor.execute("""
            UPDATE order_recommendation_log
            SET timestamp = ?, predicted_sales_qty = ?, safety_stock = ?, current_stock = ?,
                recommended_order_qty = ?, owner_adjusted_qty = ?, is_submitted = 1,
                workflow_status = ?, adjust_reason_code = ?, adjust_reason_note = ?,
                sns_uplift_applied = ?, event_uplift_applied = ?
            WHERE id = ?
        """, (
            timestamp_str, predicted_sales, safety_stock, current_stock,
            recommended_order, adjusted_order, workflow_status,
            adjust_reason_code, adjust_reason_note, sns_uplift, event_uplift,
            existing[0],
        ))
    else:
        cursor.execute("""
            INSERT INTO order_recommendation_log
            (timestamp, date, store_id, product_id, predicted_sales_qty, safety_stock,
             current_stock, recommended_order_qty, owner_adjusted_qty, is_submitted,
             workflow_status, adjust_reason_code, adjust_reason_note,
             sns_uplift_applied, event_uplift_applied)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """, (
            timestamp_str, date_str, store_id, product_id, predicted_sales, safety_stock,
            current_stock, recommended_order, adjusted_order, workflow_status,
            adjust_reason_code, adjust_reason_note, sns_uplift, event_uplift,
        ))
        
    conn.commit()
    conn.close()

def get_feedback_history(store_id=None):
    """Retrieves the logged feedback records as a Pandas DataFrame."""
    conn = get_connection()
    query = "SELECT * FROM order_recommendation_log"
    params = []
    
    if store_id:
        query += " WHERE store_id = ?"
        params.append(store_id)
        
    query += " ORDER BY timestamp DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_feedback_metrics(store_id=None):
    """
    Calculates operational feedback metrics:
    - total_confirmed_items: number of ordered items
    - matches_recommendation: items where owner accepted AI recommendation perfectly
    - acceptance_rate: ratio of matches to total confirmed
    - avg_deviation: average deviation between owner quantity and AI recommended quantity
    """
    df = get_feedback_history(store_id)
    if df.empty:
        return {
            "total_items": 0,
            "acceptance_rate": 0.0,
            "avg_deviation": 0.0,
            "adoptions": 0,
            "overrides": 0
        }
        
    total_items = len(df)
    adoptions = sum(df["recommended_order_qty"] == df["owner_adjusted_qty"])
    overrides = total_items - adoptions
    acceptance_rate = round((adoptions / total_items) * 100, 1)
    
    # Average absolute deviation for overridden quantities
    deviations = (df["owner_adjusted_qty"] - df["recommended_order_qty"]).abs()
    avg_deviation = round(deviations.mean(), 2)
    
    return {
        "total_items": total_items,
        "acceptance_rate": acceptance_rate,
        "avg_deviation": avg_deviation,
        "adoptions": adoptions,
        "overrides": overrides
    }

def save_external_signal_log(
    date_str, store_id, payload_json, total_sns_uplift=0.0, total_event_uplift=0.0
):
    conn = get_connection()
    cursor = conn.cursor()
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO external_signal_log
        (timestamp, date, store_id, signal_type, payload_json, total_sns_uplift, total_event_uplift)
        VALUES (?, ?, ?, 'combined', ?, ?, ?)
    """, (
        timestamp_str, date_str, store_id, payload_json,
        total_sns_uplift, total_event_uplift,
    ))
    conn.commit()
    conn.close()


def get_external_signal_history(store_id=None, limit=20):
    conn = get_connection()
    query = "SELECT * FROM external_signal_log"
    params = []
    if store_id:
        query += " WHERE store_id = ?"
        params.append(store_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# Self-initialization call when loaded
init_db()
