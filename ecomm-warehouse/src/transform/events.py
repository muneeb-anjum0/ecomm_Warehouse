# src/transform/events.py
"""Transform raw events to staging"""

import logging
from datetime import datetime
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)

ALLOWED_EVENT_TYPES = {'page_view', 'add_to_cart', 'purchase', 'view_product', 'checkout'}


def transform_events_to_staging(run_date: str) -> int:
    """
    Transform raw events to staging layer.
    Applies cleaning, normalization, and deduplication.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records inserted into staging
    """
    logger.info(f"Starting events transformation for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        # Delete existing staging records for this run_date (idempotent)
        delete_query = "DELETE FROM staging.events_clean WHERE load_date = %s"
        db.execute_update(delete_query, (run_date,))
        logger.info(f"Cleared existing staging records for {run_date}")
        
        # Transform and insert
        insert_query = """
            INSERT INTO staging.events_clean 
            (event_id, user_id, product_id, event_type, event_ts, load_date)
            SELECT
                event_id,
                user_id,
                CASE 
                    WHEN product_id = '' THEN NULL
                    ELSE product_id 
                END AS product_id,
                LOWER(event_type) AS event_type,
                event_ts,
                %s::DATE AS load_date
            FROM raw.events_csv
            WHERE run_date = %s
                AND event_id IS NOT NULL
                AND user_id IS NOT NULL
                AND event_ts IS NOT NULL
                AND event_type IS NOT NULL
            ON CONFLICT (event_id, load_date) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                product_id = EXCLUDED.product_id,
                event_type = EXCLUDED.event_type,
                event_ts = EXCLUDED.event_ts,
                updated_at = NOW()
        """
        
        inserted = db.execute_update(insert_query, (run_date, run_date))
        logger.info(f"Transformed {inserted} events to staging")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error transforming events: {e}")
        raise


if __name__ == "__main__":
    transform_events_to_staging("2025-12-19")
