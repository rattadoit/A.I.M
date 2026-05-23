import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join("data", "smart_order_feedback.db")

def get_connection():
    """Returns a connection to the SQLite database. Ensures directories exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the feedback SQLite database and tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create order_recommendation_log table
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
            is_submitted INTEGER NOT NULL DEFAULT 1,
            original_price REAL DEFAULT 0.0,
            discount_price REAL DEFAULT 0.0,
            discount_rate REAL DEFAULT 0.0,
            promotion_type TEXT DEFAULT 'None',
            is_1plus1 INTEGER DEFAULT 0,
            is_2plus1 INTEGER DEFAULT 0,
            promotion_start_date TEXT DEFAULT 'None',
            promotion_end_date TEXT DEFAULT 'None'
        )
    """)
    
    # Ensure columns exist (for migration of existing databases)
    cursor.execute("PRAGMA table_info(order_recommendation_log)")
    cols = [col[1] for col in cursor.fetchall()]
    migration_cols = {
        "original_price": "REAL DEFAULT 0.0",
        "discount_price": "REAL DEFAULT 0.0",
        "discount_rate": "REAL DEFAULT 0.0",
        "promotion_type": "TEXT DEFAULT 'None'",
        "is_1plus1": "INTEGER DEFAULT 0",
        "is_2plus1": "INTEGER DEFAULT 0",
        "promotion_start_date": "TEXT DEFAULT 'None'",
        "promotion_end_date": "TEXT DEFAULT 'None'"
    }
    for col_name, col_type in migration_cols.items():
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE order_recommendation_log ADD COLUMN {col_name} {col_type}")
            
    conn.commit()
    conn.close()
    print("Database initialized successfully at:", DB_PATH)

def save_recommendation_feedback(
    date_str, store_id, product_id, predicted_sales, safety_stock, current_stock, recommended_order, adjusted_order,
    original_price=0.0, discount_price=0.0, discount_rate=0.0, promotion_type="None", 
    is_1plus1=0, is_2plus1=0, promotion_start_date="None", promotion_end_date="None"
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
                original_price = ?, discount_price = ?, discount_rate = ?, promotion_type = ?,
                is_1plus1 = ?, is_2plus1 = ?, promotion_start_date = ?, promotion_end_date = ?
            WHERE id = ?
        """, (
            timestamp_str, predicted_sales, safety_stock, current_stock, recommended_order, adjusted_order,
            original_price, discount_price, discount_rate, promotion_type,
            is_1plus1, is_2plus1, promotion_start_date, promotion_end_date,
            existing[0]
        ))
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO order_recommendation_log 
            (timestamp, date, store_id, product_id, predicted_sales_qty, safety_stock, current_stock, recommended_order_qty, owner_adjusted_qty, is_submitted,
             original_price, discount_price, discount_rate, promotion_type, is_1plus1, is_2plus1, promotion_start_date, promotion_end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp_str, date_str, store_id, product_id, predicted_sales, safety_stock, current_stock, recommended_order, adjusted_order,
            original_price, discount_price, discount_rate, promotion_type, is_1plus1, is_2plus1, promotion_start_date, promotion_end_date
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

# Self-initialization call when loaded
init_db()
