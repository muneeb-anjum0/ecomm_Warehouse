# src/extract/api_orders.py
"""Extract orders (carts) from DummyJSON API in real-time"""

import requests
import json
from datetime import datetime
import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)

# DummyJSON API - free, no auth, 50 carts with rich data
DUMMYJSON_API = "https://dummyjson.com"


def extract_orders_from_api(run_date: str = None) -> int:
    """
    Fetch carts/orders from DummyJSON API (50 carts with product details).
    Carts represent orders in this API.
    
    Args:
        run_date: Optional date filter (API returns all, we'll tag with run_date)
        
    Returns:
        Number of carts/orders inserted
    """
    if run_date is None:
        run_date = datetime.utcnow().date().isoformat()
    
    logger.info(f"Fetching carts (orders) from {DUMMYJSON_API}")
    
    try:
        # Get all carts from API (limit=0 returns all)
        resp = requests.get(f"{DUMMYJSON_API}/carts?limit=0", timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        carts = data.get('carts', [])
        logger.info(f"Fetched {len(carts)} carts from DummyJSON API (total: {data.get('total', 0)})")
        
        if not carts:
            logger.warning("No carts returned from API")
            return 0
        
        # Transform carts into order format and insert
        db = DatabaseConnection()
        
        records = []
        for cart in carts:
            # Transform DummyJSON cart to order (has totals, discounts, product details)
            order = {
                "order_id": f"CART_{cart['id']}",
                "user_id": str(cart.get('userId', 'unknown')),
                "products": cart.get('products', []),  # rich product data with prices
                "total": float(cart.get('total', 0)),
                "discounted_total": float(cart.get('discountedTotal', 0)),
                "total_products": cart.get('totalProducts', 0),
                "total_quantity": cart.get('totalQuantity', 0),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            records.append((
                run_date,
                "api:dummyjson.com/carts",
                datetime.utcnow(),
                json.dumps(order)
            ))
        
        # Insert into raw.orders_json
        query = """
            INSERT INTO raw.orders_json (run_date, file_name, ingested_at, raw_json)
            VALUES (%s, %s, %s, %s)
        """
        
        inserted = db.execute_batch(query, records)
        logger.info(f"Inserted {inserted} orders from API into raw.orders_json")
        
        return inserted
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Error extracting orders from API: {e}")
        raise


if __name__ == "__main__":
    extract_orders_from_api()
