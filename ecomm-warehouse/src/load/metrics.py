# src/load/metrics.py
"""Load metrics table"""

import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def load_daily_metrics(run_date: str, runtime_seconds: int = None) -> int:
    """
    Load daily metrics summarizing the pipeline run.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        runtime_seconds: Total runtime in seconds
        
    Returns:
        Number of records inserted/updated
    """
    logger.info(f"Loading daily metrics for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        query = """
            INSERT INTO warehouse.daily_metrics 
            (run_date, raw_orders_count, staging_orders_count, fact_orders_count, 
             raw_events_count, staging_events_count, fact_events_count, dq_failed_count, runtime_seconds)
            SELECT
                %s::DATE,
                (SELECT COUNT(*) FROM raw.orders_json WHERE run_date = %s),
                (SELECT COUNT(*) FROM staging.orders_clean WHERE load_date = %s),
                (SELECT COUNT(*) FROM warehouse.fact_orders WHERE load_date = %s),
                (SELECT COUNT(*) FROM raw.events_csv WHERE run_date = %s),
                (SELECT COUNT(*) FROM staging.events_clean WHERE load_date = %s),
                (SELECT COUNT(*) FROM warehouse.fact_events WHERE load_date = %s),
                (SELECT COUNT(*) FROM audit.dq_failures WHERE run_date = %s),
                %s
            ON CONFLICT (run_date) DO UPDATE SET
                raw_orders_count = EXCLUDED.raw_orders_count,
                staging_orders_count = EXCLUDED.staging_orders_count,
                fact_orders_count = EXCLUDED.fact_orders_count,
                raw_events_count = EXCLUDED.raw_events_count,
                staging_events_count = EXCLUDED.staging_events_count,
                fact_events_count = EXCLUDED.fact_events_count,
                dq_failed_count = EXCLUDED.dq_failed_count,
                runtime_seconds = EXCLUDED.runtime_seconds,
                updated_at = NOW()
        """
        
        params = (run_date,) * 8 + (runtime_seconds,)
        inserted = db.execute_update(query, params)
        logger.info(f"Loaded metrics for {run_date}")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error loading metrics: {e}")
        raise


if __name__ == "__main__":
    load_daily_metrics("2025-12-19", runtime_seconds=300)
