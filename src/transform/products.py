# src/transform/products.py
"""Transform raw products to staging"""

import logging
import json
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def transform_products_to_staging(run_date: str) -> int:
    """
    Transform raw products to staging layer.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records inserted into staging
    """
    logger.info(f"Starting products transformation for {run_date}")
    
    db = DatabaseConnection()
    
    try:
        # Delete existing staging records for this run_date (idempotent)
        delete_query = "DELETE FROM staging.products_clean WHERE load_date = %s"
        db.execute_update(delete_query, (run_date,))
        logger.info(f"Cleared existing staging records for {run_date}")
        
        # Transform and insert
        insert_query = """
            INSERT INTO staging.products_clean 
            (product_id, product_name, category, brand, current_price, load_date)
            SELECT
                (raw_json->>'product_id')::VARCHAR AS product_id,
                (raw_json->>'product_name')::VARCHAR,
                (raw_json->>'category')::VARCHAR,
                (raw_json->>'brand')::VARCHAR,
                (raw_json->>'current_price')::DECIMAL,
                %s::DATE AS load_date
            FROM raw.products_json
            WHERE run_date = %s
                AND raw_json IS NOT NULL
                AND (raw_json->>'product_id') IS NOT NULL
            ON CONFLICT (product_id, load_date) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                brand = EXCLUDED.brand,
                current_price = EXCLUDED.current_price,
                updated_at = NOW()
        """
        
        inserted = db.execute_update(insert_query, (run_date, run_date))
        logger.info(f"Transformed {inserted} products to staging")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error transforming products: {e}")
        raise


if __name__ == "__main__":
    transform_products_to_staging("2025-12-19")
