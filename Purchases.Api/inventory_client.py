import os
import requests

INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "http://localhost:5143")

def lookup_products(company_cen, product_cens):
    if not product_cens:
        return []
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/products/lookup"
        res = requests.post(url, json={"productCens": product_cens}, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Error in lookup_products: {e}")
    return []

def increase_stock(company_cen, product_cen, quantity):
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/increase"
        res = requests.post(url, json={
            "productCen": product_cen,
            "quantity": quantity,
            "reference": "PURCHASE",
            "notes": "Purchase order confirmation"
        }, timeout=5)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"Error in increase_stock: {e}")
    return False
