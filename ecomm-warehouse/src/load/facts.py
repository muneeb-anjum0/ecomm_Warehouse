# src/load/facts.py
"""Load fact tables"""

import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def load_fact_orders(run_date: str) -> int:
    """
    Load orders into fact_orders from staging.
    Idempotent: deletes existing records for the load_date before inserting.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records inserted
    """
    logger.info(f"Loading fact_orders for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        # Delete existing records for idempotency
        delete_query = "DELETE FROM warehouse.fact_orders WHERE load_date = %s"
        db.execute_update(delete_query, (run_date,))
        logger.info(f"Cleared existing fact_orders for {run_date}")
        
        # Insert new records
        insert_query = """
            INSERT INTO warehouse.fact_orders 
            (order_id, user_id, product_id, date_id, quantity, revenue, order_ts, status, load_date)
            SELECT
                so.order_id,
                so.user_id,
                so.product_id,
                TO_CHAR(so.order_ts::DATE, 'YYYYMMDD')::INTEGER AS date_id,
                so.quantity,
                so.revenue,
                so.order_ts,
                so.status,
                %s::DATE AS load_date
            FROM staging.orders_clean so
            WHERE so.load_date = %s
                AND EXISTS (SELECT 1 FROM warehouse.dim_date WHERE date_id = TO_CHAR(so.order_ts::DATE, 'YYYYMMDD')::INTEGER)
                AND EXISTS (SELECT 1 FROM warehouse.dim_product WHERE product_id = so.product_id)
                AND EXISTS (SELECT 1 FROM warehouse.dim_user WHERE user_id = so.user_id)
        """
        
        inserted = db.execute_update(insert_query, (run_date, run_date))
        logger.info(f"Loaded {inserted} orders into fact_orders")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error loading fact_orders: {e}")
        raise


def load_fact_events(run_date: str) -> int:
    """
    Load events into fact_events from staging.
    Idempotent: deletes existing records for the load_date before inserting.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records inserted
    """
    logger.info(f"Loading fact_events for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        # Delete existing records for idempotency
        delete_query = "DELETE FROM warehouse.fact_events WHERE load_date = %s"
        db.execute_update(delete_query, (run_date,))
        logger.info(f"Cleared existing fact_events for {run_date}")
        
        # Insert new records
        insert_query = """
            INSERT INTO warehouse.fact_events 
            (event_id, user_id, product_id, date_id, event_type, event_ts, load_date)
            SELECT
                se.event_id,
                se.user_id,
                se.product_id,
                TO_CHAR(se.event_ts::DATE, 'YYYYMMDD')::INTEGER AS date_id,
                se.event_type,
                se.event_ts,
                %s::DATE AS load_date
            FROM staging.events_clean se
            WHERE se.load_date = %s
                AND EXISTS (SELECT 1 FROM warehouse.dim_date WHERE date_id = TO_CHAR(se.event_ts::DATE, 'YYYYMMDD')::INTEGER)
                AND EXISTS (SELECT 1 FROM warehouse.dim_user WHERE user_id = se.user_id)
        """
        
        inserted = db.execute_update(insert_query, (run_date, run_date))
        logger.info(f"Loaded {inserted} events into fact_events")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error loading fact_events: {e}")
        raise


if __name__ == "__main__":
    load_fact_orders("2025-12-19")
    load_fact_events("2025-12-19")
