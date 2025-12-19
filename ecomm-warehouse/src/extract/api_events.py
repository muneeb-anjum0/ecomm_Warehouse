# src/extract/api_events.py
"""Extract events from DummyJSON API in real-time"""

import requests
import json
from datetime import datetime
import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)

DUMMYJSON_API = "https://dummyjson.com"


def extract_events_from_api(run_date: str = None) -> int:
    """
    Generate synthetic clickstream events from DummyJSON API products/carts.
    Since the API doesn't have raw events, we'll create "product_view" events 
    for each product and "add_to_cart" events for each cart item.
    
    Args:
        run_date: Optional date (defaults to today)
        
    Returns:
        Number of events generated
    """
    if run_date is None:
        run_date = datetime.utcnow().date().isoformat()
    
    logger.info(f"Generating synthetic events from {DUMMYJSON_API}")
    
    try:
        # Fetch products and carts to generate events
        products_resp = requests.get(f"{DUMMYJSON_API}/products?limit=0", timeout=30)
        products_resp.raise_for_status()
        products_data = products_resp.json()
        products = products_data.get('products', [])
        
        carts_resp = requests.get(f"{DUMMYJSON_API}/carts?limit=0", timeout=30)
        carts_resp.raise_for_status()
        carts_data = carts_resp.json()
        carts = carts_data.get('carts', [])
        
        logger.info(f"Fetched {len(products)} products and {len(carts)} carts from DummyJSON")
        
        db = DatabaseConnection()
        records = []
        event_id_counter = 0
        
        # Generate "view_product" events for each product
        for product in products:
            event_id_counter += 1
            event = {
                "event_id": f"EVT_{run_date}_view_{product['id']}_{event_id_counter}",
                "user_id": str((product['id'] % 10) + 1),  # Simulate user ID
                "product_id": str(product['id']),
                "event_type": "view_product",
                "timestamp": datetime.utcnow().isoformat(),
                "product_title": product['title']
            }
            records.append((
                run_date,
                "api:fakestoreapi.com/products",
                event['event_id'],
                str((product['id'] % 10) + 1),
                str(product['id']),
                "view_product",
                datetime.utcnow(),
                json.dumps(event)
            ))
        
        # Generate "add_to_cart" events for cart items
        for cart in carts:
            for product_item in cart['products']:
                event_id_counter += 1
                event = {
                    "event_id": f"EVT_{run_date}_addcart_{product_item['productId']}_{event_id_counter}",
                    "user_id": str(cart['userId']),
                    "product_id": str(product_item['productId']),
                    "event_type": "add_to_cart",
                    "quantity": product_item['quantity'],
                    "timestamp": cart['date']
                }
                records.append((
                    run_date,
                    "api:fakestoreapi.com/carts",
                    event['event_id'],
                    str(cart['userId']),
                    str(product_item['productId']),
                    "add_to_cart",
                    cart['date'],
                    json.dumps(event)
                ))
        
        # Insert into raw.events_csv
        query = """
            INSERT INTO raw.events_csv 
            (run_date, file_name, event_id, user_id, product_id, event_type, event_ts, raw_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        inserted = db.execute_batch(query, records)
        logger.info(f"Inserted {inserted} synthetic events from API into raw.events_csv")
        
        return inserted
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Error extracting events from API: {e}")
        raise


if __name__ == "__main__":
    extract_events_from_api()
