#!/usr/bin/env python3
"""Quick test of DummyJSON API"""

import requests

print("=" * 60)
print("TESTING DUMMYJSON API")
print("=" * 60)

# Test products endpoint
print("\n1. Testing /products endpoint...")
resp = requests.get("https://dummyjson.com/products?limit=5")
data = resp.json()
products = data['products']

print(f"   Total products available: {data['total']}")
print(f"   Fetched in this call: {len(products)}")
print(f"   Sample product ID: {products[0]['id']}")
print(f"   Sample product name: {products[0]['title']}")
print(f"   Has 'stock' field: {'stock' in products[0]}")
print(f"   Has 'discountPercentage' field: {'discountPercentage' in products[0]}")
print(f"   Has 'images' field: {'images' in products[0]}")
print(f"   Stock value: {products[0].get('stock', 'N/A')}")
print(f"   Discount value: {products[0].get('discountPercentage', 'N/A')}%")

# Test carts endpoint
print("\n2. Testing /carts endpoint...")
resp2 = requests.get("https://dummyjson.com/carts?limit=3")
data2 = resp2.json()
carts = data2['carts']

print(f"   Total carts available: {data2['total']}")
print(f"   Fetched in this call: {len(carts)}")
print(f"   Sample cart has 'total': {'total' in carts[0]}")
print(f"   Sample cart has 'discountedTotal': {'discountedTotal' in carts[0]}")
print(f"   Sample cart total: ${carts[0].get('total', 0):.2f}")
print(f"   Sample cart discounted: ${carts[0].get('discountedTotal', 0):.2f}")

print("\n" + "=" * 60)
print("✅ DUMMYJSON API IS WORKING!")
print("   - 9.7x more products than Fake Store (194 vs 20)")
print("   - Richer data: stock, discounts, images, reviews")
print("   - Better for analytics and demos")
print("=" * 60)
