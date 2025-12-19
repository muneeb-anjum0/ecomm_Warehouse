# src/extract/api_products.py
"""Extract products from DummyJSON API in real-time"""

import requests
import json
from datetime import datetime
import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)

DUMMYJSON_API = "https://dummyjson.com"


def extract_products_from_api(run_date: str = None) -> int:
    """
    Fetch products from DummyJSON API (194 products with rich data).
    
    Args:
        run_date: Optional date (defaults to today)
        
    Returns:
        Number of products inserted
    """
    if run_date is None:
        run_date = datetime.utcnow().date().isoformat()
    
    logger.info(f"Fetching products from {DUMMYJSON_API}")
    
    try:
        # Get all products (limit=0 returns all 194 products)
        resp = requests.get(f"{DUMMYJSON_API}/products?limit=0", timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        products = data.get('products', [])
        logger.info(f"Fetched {len(products)} products from DummyJSON API (total: {data.get('total', 0)})")
        
        if not products:
            logger.warning("No products returned from API")
            return 0
        
        db = DatabaseConnection()
        
        records = []
        for product in products:
            # Normalize DummyJSON product data (has stock, discount, reviews, images)
            product_data = {
                "product_id": str(product['id']),
                "product_name": product['title'],
                "category": product.get('category', 'uncategorized'),
                "brand": product.get('brand', 'Fake Store'),
                "description": product['description'],
                "current_price": float(product['price']),
                "rating": product.get('rating', {}).get('rate', 0),
                "count": product.get('rating', {}).get('count', 0)
            }
            
            records.append((
                run_date,
                datetime.utcnow(),
                json.dumps(product_data)
            ))
        
        # Insert into raw.products_json
        query = """
            INSERT INTO raw.products_json (run_date, fetched_at, raw_json)
            VALUES (%s, %s, %s)
        """
        
        inserted = db.execute_batch(query, records)
        logger.info(f"Inserted {inserted} products from API into raw.products_json")
        
        return inserted
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Error extracting products from API: {e}")
        raise


if __name__ == "__main__":
    extract_products_from_api()
