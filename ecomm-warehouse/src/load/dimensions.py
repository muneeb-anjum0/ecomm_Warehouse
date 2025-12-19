# src/load/dimensions.py
"""Load dimension tables"""

import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def load_dim_product(run_date: str) -> int:
    """
    Load/upsert products into dim_product from staging.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records upserted
    """
    logger.info(f"Loading dim_product for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        query = """
            INSERT INTO warehouse.dim_product 
            (product_id, product_name, category, brand, current_price, effective_from)
            SELECT
                product_id,
                product_name,
                category,
                brand,
                current_price,
                %s::DATE
            FROM staging.products_clean
            WHERE load_date = %s
                AND product_id IS NOT NULL
            ON CONFLICT (product_id) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                brand = EXCLUDED.brand,
                current_price = EXCLUDED.current_price,
                updated_at = NOW()
        """
        
        inserted = db.execute_update(query, (run_date, run_date))
        logger.info(f"Loaded {inserted} products into dim_product")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error loading dim_product: {e}")
        raise


def load_dim_user(run_date: str) -> int:
    """
    Load/upsert users into dim_user from staging orders.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records upserted
    """
    logger.info(f"Loading dim_user for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        query = """
            INSERT INTO warehouse.dim_user (user_id)
            SELECT DISTINCT user_id
            FROM staging.orders_clean
            WHERE load_date = %s
                AND user_id IS NOT NULL
            ON CONFLICT (user_id) DO UPDATE SET
                updated_at = NOW()
        """
        
        inserted = db.execute_update(query, (run_date,))
        logger.info(f"Loaded {inserted} users into dim_user")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error loading dim_user: {e}")
        raise


def load_dim_date(run_date: str) -> int:
    """
    Load date dimension for a specific date.
    (Usually pre-populated but this ensures coverage)
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records inserted
    """
    logger.info(f"Loading dim_date for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        query = """
            INSERT INTO warehouse.dim_date 
            (date_id, date, day, week, month, quarter, year, day_of_week, day_name, is_weekend)
            SELECT
                TO_CHAR(%s::DATE, 'YYYYMMDD')::INTEGER,
                %s::DATE,
                EXTRACT(DAY FROM %s::DATE)::INTEGER,
                EXTRACT(WEEK FROM %s::DATE)::INTEGER,
                EXTRACT(MONTH FROM %s::DATE)::INTEGER,
                EXTRACT(QUARTER FROM %s::DATE)::INTEGER,
                EXTRACT(YEAR FROM %s::DATE)::INTEGER,
                EXTRACT(DOW FROM %s::DATE)::INTEGER,
                TO_CHAR(%s::DATE, 'Day'),
                EXTRACT(DOW FROM %s::DATE) IN (0, 6)
            ON CONFLICT (date_id) DO NOTHING
        """
        
        params = (run_date,) * 10
        inserted = db.execute_update(query, params)
        logger.info(f"Loaded date dimension for {run_date}")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error loading dim_date: {e}")
        raise


if __name__ == "__main__":
    load_dim_product("2025-12-19")
    load_dim_user("2025-12-19")
    load_dim_date("2025-12-19")
