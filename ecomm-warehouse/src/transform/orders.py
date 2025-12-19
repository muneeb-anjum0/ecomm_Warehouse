# src/transform/orders.py
"""Transform raw orders to staging"""

import logging
from decimal import Decimal
from datetime import datetime
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def transform_orders_to_staging(run_date: str) -> int:
    """
    Transform raw orders to staging layer.
    Applies cleaning, validation, and deduplication.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records inserted into staging
    """
    logger.info(f"Starting orders transformation for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        # Delete existing staging records for this run_date (idempotent)
        delete_query = "DELETE FROM staging.orders_clean WHERE load_date = %s"
        db.execute_update(delete_query, (run_date,))
        logger.info(f"Cleared existing staging records for {run_date}")
        
        # Transform and insert
        insert_query = """
            INSERT INTO staging.orders_clean 
            (order_id, user_id, product_id, quantity, unit_price, revenue, order_ts, status, load_date)
            SELECT
                (r.raw_json->>'order_id')::VARCHAR AS order_id,
                (r.raw_json->>'user_id')::VARCHAR AS user_id,
                (r.raw_json->>'product_id')::VARCHAR AS product_id,
                (r.raw_json->>'quantity')::INTEGER AS quantity,
                (r.raw_json->>'price')::DECIMAL AS unit_price,
                ((r.raw_json->>'quantity')::INTEGER * (r.raw_json->>'price')::DECIMAL)::DECIMAL AS revenue,
                (r.raw_json->>'timestamp')::TIMESTAMP AS order_ts,
                (r.raw_json->>'status')::VARCHAR AS status,
                %s::DATE AS load_date
            FROM (
                SELECT DISTINCT ON ((raw_json->>'order_id')) raw_json, ingested_at
                FROM raw.orders_json
                WHERE run_date = %s
                    AND raw_json IS NOT NULL
                    AND (raw_json->>'order_id') IS NOT NULL
                ORDER BY (raw_json->>'order_id'), ingested_at DESC
            ) r
            ON CONFLICT (order_id, load_date) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                product_id = EXCLUDED.product_id,
                quantity = EXCLUDED.quantity,
                unit_price = EXCLUDED.unit_price,
                revenue = EXCLUDED.revenue,
                order_ts = EXCLUDED.order_ts,
                status = EXCLUDED.status,
                updated_at = NOW()
        """
        
        inserted = db.execute_update(insert_query, (run_date, run_date))
        logger.info(f"Transformed {inserted} orders to staging")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error transforming orders: {e}")
        raise


if __name__ == "__main__":
    transform_orders_to_staging("2025-12-19")
