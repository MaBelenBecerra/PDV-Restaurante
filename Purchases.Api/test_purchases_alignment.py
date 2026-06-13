import os
import sys

# Force pure English locale to prevent UnicodeDecodeError on PostgreSQL error messages
os.environ["LC_ALL"] = "C"
os.environ["LC_MESSAGES"] = "C"
os.environ["LANG"] = "C"

import unittest
from unittest.mock import patch
import json
import uuid
import psycopg2
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Isolated test database setup
def setup_test_database():
    try:
        # Connect to default postgres DB
        conn = psycopg2.connect(host='localhost', port=5432, database='postgres', user='postgres', password='Teto123..')
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if the isolated test database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'pdv_restaurante_align_test'")
        exists = cur.fetchone()
        if not exists:
            cur.execute("CREATE DATABASE pdv_restaurante_align_test")
            print("Created isolated test database: pdv_restaurante_align_test")
            
        cur.close()
        conn.close()
        
        # Connect to the test database and run initialization script
        conn = psycopg2.connect(host='localhost', port=5432, database='pdv_restaurante_align_test', user='postgres', password='Teto123..')
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if the 'empresas' table exists in the public schema
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'empresas')")
        schema_exists = cur.fetchone()[0]
        if not schema_exists:
            print("Initializing test database schema...")
            schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "postgres_schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
            cur.execute(sql_content)
            print("Test database schema initialized successfully.")
            
        cur.close()
        conn.close()
        
        return "Host=localhost;Database=pdv_restaurante_align_test;Username=postgres;Password=Teto123.."
    except Exception as e:
        print(f"Error setting up test database: {e}")
        return None

# Resolve and set the connection string
test_conn_str = setup_test_database()
if test_conn_str:
    os.environ["DB_CONNECTION_STRING"] = test_conn_str
else:
    # Fallback to translated connection string
    conn_str = os.environ.get("DB_CONNECTION_STRING", "")
    if "Host=postgres-db" in conn_str:
        os.environ["DB_CONNECTION_STRING"] = conn_str.replace("Host=postgres-db", "Host=localhost")

# Add the current directory to sys.path so we can import app and database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import query, execute

class TestPurchasesAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We need a test company in public.empresas
        cls.company_cen = "test-company-" + str(uuid.uuid4())[:8]
        execute(
            "INSERT INTO empresas (cen, nombre, nit, activo) VALUES (%s, %s, %s, 1) ON CONFLICT (cen) DO NOTHING",
            (cls.company_cen, f"Empresa Test Alignment {cls.company_cen}", "123456789")
        )
        
        # We also need a category and product in inventory for testing item creation
        cls.category_cen = "test-cat-" + str(uuid.uuid4())[:8]
        cls.unit_cen = "test-uni-" + str(uuid.uuid4())[:8]
        cls.product_cen = "test-prod-" + str(uuid.uuid4())[:8]
        
        # Insert category with unique name to avoid ON CONFLICT returning None
        cat_id = execute(
            "INSERT INTO categorias (nombre, cen, code) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
            (f"Cat Test Align {cls.category_cen}", cls.category_cen, f"CAT-{cls.category_cen}".upper())
        )
        if not cat_id:
            res = query("SELECT id FROM categorias WHERE cen = %s", (cls.category_cen,), fetch='one')
            cat_id = res['id'] if res else 1
            
        # Insert unit with unique name
        uni_id = execute(
            "INSERT INTO unidades (nombre, cen, code) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
            (f"Uni Test Align {cls.unit_cen}", cls.unit_cen, f"UNI-{cls.unit_cen}".upper())
        )
        if not uni_id:
            res = query("SELECT id FROM unidades WHERE cen = %s", (cls.unit_cen,), fetch='one')
            uni_id = res['id'] if res else 1
            
        # Insert product with unique name
        prod_id = execute('''
            INSERT INTO productos (nombre, categoria_id, unidad_id, precio, stock, activo, agotado, cen, code, station_code)
            VALUES (%s, %s, %s, 10.0, 0, 1, 0, %s, %s, 'COCINA')
            ON CONFLICT DO NOTHING RETURNING id
        ''', (f"Prod Test Align {cls.product_cen}", cat_id, uni_id, cls.product_cen, f"PROD-{cls.product_cen}".upper()))
        if not prod_id:
            res = query("SELECT id FROM productos WHERE cen = %s", (cls.product_cen,), fetch='one')
            prod_id = res['id'] if res else 1

    def setUp(self):
        self.client = app.test_client()

    def test_01_create_and_get_supplier(self):
        # Create a supplier
        sup_code = "SUPTEST-" + str(uuid.uuid4())[:8].upper()
        sup_name = "Proveedor Test " + sup_code
        
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/suppliers",
            data=json.dumps({"name": sup_name, "code": sup_code}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data["name"], sup_name)
        self.assertEqual(data["code"], sup_code)
        self.assertTrue(data["active"])
        supplier_cen = data["supplierCen"]
        
        # Get all suppliers and verify
        res = self.client.get(f"/api/purchases/companies/{self.company_cen}/suppliers?activeOnly=true")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(any(s["code"] == sup_code for s in data))
        
        # Get specific supplier by code
        res = self.client.get(f"/api/purchases/companies/{self.company_cen}/suppliers/{sup_code}")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["code"], sup_code)
        self.assertEqual(data["name"], sup_name)
        self.assertEqual(data["supplierCen"], supplier_cen)
        
        # Get specific supplier by CEN
        res = self.client.get(f"/api/purchases/companies/{self.company_cen}/suppliers/{supplier_cen}")
        self.assertEqual(res.status_code, 200)
        
        # Get non-existing supplier
        res = self.client.get(f"/api/purchases/companies/{self.company_cen}/suppliers/NONEXISTENT")
        self.assertEqual(res.status_code, 404)

    def test_02_create_purchase_order_flexibility(self):
        # Create a supplier code
        sup_code = "SUPFLEX-" + str(uuid.uuid4())[:8].upper()
        sup_name = "Proveedor Flex " + sup_code
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/suppliers",
            data=json.dumps({"name": sup_name, "code": sup_code}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        supplier_cen = json.loads(res.data)["supplierCen"]
        
        # 1. Create order using supplierCen (flexible: code)
        order_payload_1 = {
            "supplierCen": sup_code,
            "items": [
                {"productCen": self.product_cen, "quantity": 5}
            ]
        }
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/orders",
            data=json.dumps(order_payload_1),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        order_1 = json.loads(res.data)
        self.assertEqual(order_1["supplier"], sup_name)
        self.assertEqual(order_1["status"], "DRAFT")
        self.assertEqual(len(order_1["items"]), 1)
        self.assertEqual(order_1["items"][0]["quantity"], 5)
        
        # 2. Create order using supplier (flexible: code)
        order_payload_2 = {
            "supplier": sup_code,
            "items": [
                {"productCen": self.product_cen, "quantity": 10}
            ]
        }
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/orders",
            data=json.dumps(order_payload_2),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        
        # 3. Create order skipping invalid items
        order_payload_3 = {
            "supplierCen": supplier_cen,
            "items": [
                {"productCen": self.product_cen, "quantity": 3},        # valid
                {"productCen": self.product_cen, "quantity": -2},       # invalid: < 1
                {"productCen": self.product_cen, "quantity": 2.5},      # invalid: float
                {"productCen": "nonexistent-prod", "quantity": 5}      # invalid: prod not found
            ]
        }
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/orders",
            data=json.dumps(order_payload_3),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        order_3 = json.loads(res.data)
        self.assertEqual(len(order_3["items"]), 1)
        self.assertEqual(order_3["items"][0]["quantity"], 3)
        
        # 4. Create order with only invalid items (should return 400 Bad Request)
        order_payload_4 = {
            "supplierCen": supplier_cen,
            "items": [
                {"productCen": self.product_cen, "quantity": 0},
                {"productCen": self.product_cen, "quantity": 1.5}
            ]
        }
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/orders",
            data=json.dumps(order_payload_4),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_03_get_orders_pagination_and_filtering(self):
        # Retrieve orders
        res = self.client.get(f"/api/purchases/companies/{self.company_cen}/orders?page=1&pageSize=2&sortDescending=true")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertIn("totalCount", data)
        self.assertIn("page", data)
        self.assertIn("pageSize", data)
        self.assertIn("totalPages", data)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["pageSize"], 2)
        
        # Get specific order status
        res = self.client.get(f"/api/purchases/companies/{self.company_cen}/orders?status=DRAFT")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        for item in data["items"]:
            self.assertEqual(item["status"], "DRAFT")

    @patch("inventory_client.increase_stock")
    def test_04_confirm_and_cancel_transitions(self, mock_increase_stock):
        mock_increase_stock.return_value = True
        
        # Create a supplier
        sup_code = "SUPTRANS-" + str(uuid.uuid4())[:8].upper()
        sup_name = "Proveedor Trans " + sup_code
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/suppliers",
            data=json.dumps({"name": sup_name, "code": sup_code}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        supplier_cen = json.loads(res.data)["supplierCen"]
        
        # Create an order
        order_payload = {
            "supplierCen": supplier_cen,
            "items": [
                {"productCen": self.product_cen, "quantity": 4}
            ]
        }
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/orders",
            data=json.dumps(order_payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        order_cen = json.loads(res.data)["orderCen"]
        
        # Confirm the order
        res = self.client.post(f"/api/purchases/companies/{self.company_cen}/orders/{order_cen}/confirm")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "CONFIRMED")
        
        # Confirming again should return 409 Conflict
        res = self.client.post(f"/api/purchases/companies/{self.company_cen}/orders/{order_cen}/confirm")
        self.assertEqual(res.status_code, 409)
        
        # Cancelling a confirmed order should return 409 Conflict
        res = self.client.post(f"/api/purchases/companies/{self.company_cen}/orders/{order_cen}/cancel")
        self.assertEqual(res.status_code, 409)
        
        # Create another order to test cancel transition
        res = self.client.post(
            f"/api/purchases/companies/{self.company_cen}/orders",
            data=json.dumps(order_payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        order_cen_2 = json.loads(res.data)["orderCen"]
        
        # Cancel the second order
        res = self.client.post(f"/api/purchases/companies/{self.company_cen}/orders/{order_cen_2}/cancel")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "CANCELLED")
        
        # Cancelling again should return 409 Conflict
        res = self.client.post(f"/api/purchases/companies/{self.company_cen}/orders/{order_cen_2}/cancel")
        self.assertEqual(res.status_code, 409)

if __name__ == "__main__":
    unittest.main()
