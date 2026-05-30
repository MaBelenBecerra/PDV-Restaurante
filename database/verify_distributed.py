import requests
import sys
import json

INV_URL = "http://localhost:5143"
SAL_URL = "http://localhost:5074"
PUR_URL = "http://localhost:5229"

print("=" * 60)
print("RUNNING DISTRIBUTED MICROSERVICES VERIFICATION")
print("=" * 60)

# 1. Verify health of each service
for name, url in [("Inventory", INV_URL), ("Sales", SAL_URL), ("Purchases", PUR_URL)]:
    try:
        res = requests.get(f"{url}/health", timeout=3)
        print(f"{name} Health check status: {res.status_code}")
        assert res.status_code == 200
        data = res.json()
        print(f"Response: {data}")
    except Exception as e:
        print(f"Error checking health for {name} ({url}): {e}")
        print("Please make sure all three servers are running!")
        sys.exit(1)

print("\nHealth checks passed!\n")

# 2. Get companies
try:
    res = requests.get(f"{INV_URL}/api/inventory/companies")
    assert res.status_code == 200
    companies = res.json()
    assert len(companies) > 0
    company_cen = companies[0]['cen']
    print(f"Retrieved Company CEN: {company_cen}")
except Exception as e:
    print(f"Failed to get companies: {e}")
    sys.exit(1)

# 3. Get products
try:
    res = requests.get(f"{INV_URL}/api/inventory/companies/{company_cen}/products")
    assert res.status_code == 200
    products_data = res.json()
    assert 'items' in products_data
    items = products_data['items']
    print(f"Total products in inventory: {products_data['totalCount']}")
    if items:
        test_product = items[0]
        print(f"Selected test product: {test_product['name']} (CEN: {test_product['cen']}, Stock: {test_product['price']})")
    else:
        print("No products found to run stock tests.")
        sys.exit(1)
except Exception as e:
    print(f"Failed to query products: {e}")
    sys.exit(1)

# 4. Check initial stock of the test product
product_cen = test_product['cen']
try:
    res = requests.get(f"{INV_URL}/api/inventory/companies/{company_cen}/stock")
    assert res.status_code == 200
    stock_list = res.json()
    stock_item = next(s for s in stock_list if s['productCen'] == product_cen)
    initial_stock = stock_item['quantity']
    print(f"Initial Stock for {test_product['name']}: {initial_stock}")
except Exception as e:
    print(f"Failed to check initial stock: {e}")
    sys.exit(1)

# 5. Create a Ticket (Sales API)
try:
    res = requests.post(
        f"{SAL_URL}/api/sales/companies/{company_cen}/tickets",
        json={"mesero": "Mesero Distribuido Test"}
    )
    assert res.status_code == 201
    ticket = res.json()
    ticket_cen = ticket['cen']
    print(f"Created Ticket {ticket['ticketNumber']} (CEN: {ticket_cen})")
except Exception as e:
    print(f"Failed to create ticket: {e}")
    sys.exit(1)

# 6. Add Item to Ticket (Sales API -> triggers stock validation HTTP request to Inventory API)
try:
    res = requests.post(
        f"{SAL_URL}/api/sales/companies/{company_cen}/tickets/{ticket_cen}/items",
        json={"productCen": product_cen, "quantity": 2}
    )
    print(f"Add Item Status: {res.status_code}")
    if res.status_code != 201:
        print(f"Response: {res.text}")
    assert res.status_code == 201
    added_item = res.json()
    print("Added 2 units to ticket successfully.")
except Exception as e:
    print(f"Failed to add item to ticket: {e}")
    sys.exit(1)

# 7. Pay Ticket (Sales API -> triggers stock consumption HTTP request to Inventory API)
try:
    res = requests.post(
        f"{SAL_URL}/api/sales/companies/{company_cen}/tickets/{ticket_cen}/payment",
        json={"paymentMethod": "CASH"}
    )
    print(f"Pay Ticket Status: {res.status_code}")
    if res.status_code != 200:
        print(f"Response: {res.text}")
    assert res.status_code == 200
    print("Ticket paid successfully.")
except Exception as e:
    print(f"Failed to pay ticket: {e}")
    sys.exit(1)

# 8. Check final stock in Inventory (to confirm Sales successfully decremented stock via HTTP!)
try:
    res = requests.get(f"{INV_URL}/api/inventory/companies/{company_cen}/stock")
    assert res.status_code == 200
    stock_list = res.json()
    stock_item = next(s for s in stock_list if s['productCen'] == product_cen)
    final_stock = stock_item['quantity']
    print(f"Final Stock for {test_product['name']}: {final_stock}")
    assert final_stock == initial_stock - 2
    print("VERIFICATION SUCCESS: Stock was decremented by exactly 2 units via cross-service HTTP calls!")
except Exception as e:
    print(f"Failed to verify final stock: {e}")
    sys.exit(1)

print("=" * 60)
print("ALL DISTRIBUTED VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
print("=" * 60)
