# src/extract/orders.py
"""Extract orders from daily JSON files"""

import json
import os
from datetime import datetime
from pathlib import Path
import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def extract_orders(run_date: str, data_dir: str = "/opt/airflow/data") -> int:
    """
    Extract orders from JSON file for a given run_date.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        data_dir: Root data directory path
        
    Returns:
        Number of records inserted into raw layer
    """
    logger.info(f"Starting orders extraction for {run_date}")
    
    # Construct file path: data/incoming/orders/YYYY-MM-DD/orders.json
    orders_file = Path(data_dir) / "incoming" / "orders" / run_date / "orders.json"
    
    if not orders_file.exists():
        logger.warning(f"Orders file not found: {orders_file}")
        return 0
    
    try:
        # Read JSON file
        with open(orders_file, 'r') as f:
            orders_data = json.load(f)
        
        if not isinstance(orders_data, list):
            orders_data = [orders_data]
        
        logger.info(f"Loaded {len(orders_data)} orders from {orders_file}")
        
        # Insert into raw.orders_json
        db = DatabaseConnection()
        query = """
            INSERT INTO raw.orders_json (run_date, file_name, ingested_at, raw_json)
            VALUES (%s, %s, %s, %s)
        """
        
        records = [
            (run_date, str(orders_file), datetime.now(), json.dumps(order))
            for order in orders_data
        ]
        
        inserted = db.execute_batch(query, records)
        logger.info(f"Inserted {inserted} orders into raw.orders_json")
        
        return inserted
        
    except Exception as e:
        logger.error(f"Error extracting orders: {e}")
        raise


if __name__ == "__main__":
    # Test extraction
    extract_orders("2025-12-19")
