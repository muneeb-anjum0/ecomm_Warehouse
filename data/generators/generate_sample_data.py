# data/generators/generate_sample_data.py
"""Generate sample orders and events data for testing"""

import json
import csv
import random
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configuration
NUM_ORDERS_PER_DAY = 1000
NUM_EVENTS_PER_DAY = 15000
NUM_USERS = 500
NUM_PRODUCTS = 100
PRODUCTS = [f"PROD_{i:04d}" for i in range(1, NUM_PRODUCTS + 1)]
USERS = [f"USER_{i:04d}" for i in range(1, NUM_USERS + 1)]
STATUSES = ['paid', 'cancelled', 'refunded', 'pending']
EVENT_TYPES = ['page_view', 'add_to_cart', 'purchase', 'view_product', 'checkout']

DATA_DIR = Path(__file__).parent.parent


def generate_orders(run_date: str, num_orders: int = NUM_ORDERS_PER_DAY) -> str:
    """Generate sample orders JSON"""
    orders = []
    
    date_obj = datetime.strptime(run_date, '%Y-%m-%d')
    
    for i in range(num_orders):
        order = {
            'order_id': f"ORD_{run_date.replace('-', '')}_{i:06d}",
            'user_id': random.choice(USERS),
            'product_id': random.choice(PRODUCTS),
            'quantity': random.randint(1, 10),
            'price': round(random.uniform(10, 500), 2),
            'timestamp': (date_obj + timedelta(hours=random.randint(0, 23), 
                                              minutes=random.randint(0, 59))).isoformat(),
            'status': random.choice(STATUSES)
        }
        orders.append(order)
    
    return json.dumps(orders, indent=2)


def generate_events(run_date: str, num_events: int = NUM_EVENTS_PER_DAY) -> str:
    """Generate sample events CSV"""
    
    date_obj = datetime.strptime(run_date, '%Y-%m-%d')
    
    events = []
    for i in range(num_events):
        event_type = random.choice(EVENT_TYPES)
        event = {
            'event_id': f"EVT_{run_date.replace('-', '')}_{i:07d}",
            'user_id': random.choice(USERS),
            'product_id': random.choice(PRODUCTS) if event_type != 'page_view' else '',
            'event_type': event_type,
            'event_ts': (date_obj + timedelta(hours=random.randint(0, 23), 
                                             minutes=random.randint(0, 59),
                                             seconds=random.randint(0, 59))).isoformat()
        }
        events.append(event)
    
    # Convert to CSV
    output = []
    output.append(','.join(events[0].keys()))
    for event in events:
        output.append(','.join(str(v) for v in event.values()))
    
    return '\n'.join(output)


def generate_products() -> str:
    """Generate sample products JSON"""
    CATEGORIES = ['Electronics', 'Clothing', 'Home', 'Sports', 'Books', 'Toys']
    BRANDS = ['BrandA', 'BrandB', 'BrandC', 'BrandD', 'BrandE']
    
    products = []
    for product_id in PRODUCTS:
        product = {
            'product_id': product_id,
            'product_name': f'{product_id} - {random.choice(CATEGORIES)}',
            'category': random.choice(CATEGORIES),
            'brand': random.choice(BRANDS),
            'current_price': round(random.uniform(10, 500), 2)
        }
        products.append(product)
    
    return json.dumps(products, indent=2)


def generate_data_for_date_range(start_date: str, num_days: int = 7):
    """Generate data for a range of dates"""
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    
    for day_offset in range(num_days):
        current_date = start + timedelta(days=day_offset)
        run_date = current_date.strftime('%Y-%m-%d')
        
        print(f"\n📅 Generating data for {run_date}...")
        
        # Create orders directory and file
        orders_dir = DATA_DIR / 'incoming' / 'orders' / run_date
        orders_dir.mkdir(parents=True, exist_ok=True)
        
        orders_file = orders_dir / 'orders.json'
        with open(orders_file, 'w') as f:
            f.write(generate_orders(run_date))
        print(f"  ✓ Created {orders_file}")
        
        # Create events directory and file
        events_dir = DATA_DIR / 'incoming' / 'events' / run_date
        events_dir.mkdir(parents=True, exist_ok=True)
        
        events_file = events_dir / 'events.csv'
        with open(events_file, 'w') as f:
            f.write(generate_events(run_date))
        print(f"  ✓ Created {events_file}")
        
        # Create products JSON once per week (Monday)
        if current_date.weekday() == 0:
            products_file = DATA_DIR / 'incoming' / 'products' / f'products_{run_date}.json'
            products_file.parent.mkdir(parents=True, exist_ok=True)
            with open(products_file, 'w') as f:
                f.write(generate_products())
            print(f"  ✓ Created {products_file} (Weekly products)")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
        num_days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    else:
        # Default: generate for last 7 days
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        num_days = 7
    
    print(f"{'='*60}")
    print(f"Generating sample data from {start_date} for {num_days} days")
    print(f"{'='*60}")
    
    generate_data_for_date_range(start_date, num_days)
    
    print(f"\n{'='*60}")
    print("✓ Sample data generation complete!")
    print(f"{'='*60}")
    print(f"\nGenerated data in: {DATA_DIR / 'incoming'}")
    print("\nTo generate more data, run:")
    print(f"  python {__file__} YYYY-MM-DD [num_days]")
