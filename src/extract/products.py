# src/extract/products.py
"""Extract products from file or API"""

import requests
import json
from datetime import datetime
import logging
import os
from pathlib import Path
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def extract_products(run_date: str, data_dir: str = "/opt/airflow/data") -> int:
    """
    Extract products from local file or API (fallback).
    Tries local file first, then falls back to API.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        data_dir: Root data directory path
        
    Returns:
        Number of records inserted into raw layer
    """
    logger.info(f"Starting products extraction for {run_date}")
    
    # Try local file first
    products_file = Path(data_dir) / "incoming" / "products" / f"products_{run_date}.json"
    
    if products_file.exists():
        try:
            with open(products_file, 'r') as f:
                products_data = json.load(f)
            
            if not isinstance(products_data, list):
                products_data = [products_data]
            
            logger.info(f"Loaded {len(products_data)} products from {products_file}")
            
            # Insert into raw.products_json
            db = DatabaseConnection()
            query = """
                INSERT INTO raw.products_json (run_date, fetched_at, raw_json)
                VALUES (%s, %s, %s)
            """
            
            records = [
                (run_date, datetime.now(), json.dumps(product))
                for product in products_data
            ]
            
            inserted = db.execute_batch(query, records)
            logger.info(f"Inserted {inserted} products into raw.products_json")
            
            return inserted
        except Exception as e:
            logger.error(f"Error extracting products from file: {e}")
            raise
    
    # Fallback to API
    logger.info(f"Products file not found: {products_file}, trying API...")
    
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
        logger.warning(f"Skipping products extraction - no file or API available")
        return 0
    except Exception as e:
        logger.error(f"Error extracting products: {e}")
        raise


if __name__ == "__main__":
    # Test extraction
    extract_products("2025-12-19")
