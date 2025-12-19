# src/extract/products.py
"""Extract products from API"""

import requests
import json
from datetime import datetime
import logging
import os
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def extract_products(run_date: str) -> int:
    """
    Extract products from API.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        
    Returns:
        Number of records inserted into raw layer
    """
    logger.info(f"Starting products extraction from API for {run_date}")
    
    api_url = os.getenv('PRODUCTS_API_URL', 'http://localhost:5000/api/products')
    timeout = int(os.getenv('PRODUCTS_API_TIMEOUT', 30))
    
    try:
        response = requests.get(api_url, timeout=timeout)
        response.raise_for_status()
        
        products_data = response.json()
        logger.info(f"Fetched {len(products_data) if isinstance(products_data, list) else 1} products from API")
        
        # Insert into raw.products_json
        db = DatabaseConnection()
        query = """
            INSERT INTO raw.products_json (run_date, fetched_at, raw_json)
            VALUES (%s, %s, %s)
        """
        
        record = (run_date, datetime.now(), json.dumps(products_data))
        
        inserted = db.execute_update(query, record)
        logger.info(f"Inserted products into raw.products_json")
        
        return inserted
        
    except requests.RequestException as e:
        logger.error(f"Error fetching products from API: {e}")
        raise
    except Exception as e:
        logger.error(f"Error extracting products: {e}")
        raise


if __name__ == "__main__":
    # Test extraction
    extract_products("2025-12-19")
