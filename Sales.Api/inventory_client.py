import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from dotenv import load_dotenv

# Ensure environment variables are loaded before reading them
load_dotenv()

INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "http://localhost:5143")

# Configure a resilient session with 3 retries and exponential backoff
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=2,  # Wait times: 2s, 4s, 8s (matching C# Polly backoff)
    status_forcelist=[500, 502, 503, 504],
    raise_on_status=False
)
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

class DownstreamServiceError(Exception):
    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code

def lookup_products(company_cen, product_cens):
    print("LOOKUP_PRODUCTS CONNECTING TO:", INVENTORY_API_URL, flush=True)
    if not product_cens:
        return []
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/products/lookup"
        res = session.post(url, json={"productCens": product_cens}, timeout=5)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 404:
            raise DownstreamServiceError("Compañía o productos no encontrados en inventario", 404)
        else:
            raise DownstreamServiceError(f"Error en el servicio de inventario (HTTP {res.status_code})", 502)
    except requests.exceptions.RequestException as e:
        raise DownstreamServiceError("El servicio de inventario no está disponible o no responde", 503)

def validate_stock(company_cen, product_cen, quantity):
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/validate"
        res = session.post(url, json={"productCen": product_cen, "quantity": quantity}, timeout=5)
        if res.status_code == 200:
            return res.json().get("available", False)
        elif res.status_code == 404:
            raise DownstreamServiceError("Producto no encontrado en inventario para validar stock", 404)
        else:
            raise DownstreamServiceError(f"Error en el servicio de inventario (HTTP {res.status_code})", 502)
    except requests.exceptions.RequestException as e:
        raise DownstreamServiceError("El servicio de inventario no está disponible o no responde", 503)

def consume_stock(company_cen, product_cen, quantity, notes="Ticket payment"):
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/consume"
        res = session.post(url, json={
            "productCen": product_cen,
            "quantity": quantity,
            "reference": "SALES",
            "notes": notes
        }, timeout=5)
        if res.status_code in (200, 201):
            return True
        elif res.status_code == 404:
            raise DownstreamServiceError("Producto no encontrado en inventario para descontar stock", 404)
        elif res.status_code == 409:
            raise DownstreamServiceError("Stock insuficiente en inventario para completar la venta", 409)
        else:
            raise DownstreamServiceError(f"Error al descontar stock (HTTP {res.status_code})", 502)
    except requests.exceptions.RequestException as e:
        raise DownstreamServiceError("El servicio de inventario no está disponible o no responde", 503)

def get_sellable_products(company_cen, search=None, category_cen=None, page=1, page_size=20):
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/sellable-products"
        params = {
            "search": search,
            "categoryCen": category_cen,
            "page": page,
            "pageSize": page_size
        }
        res = session.get(url, params=params, timeout=5)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 404:
            raise DownstreamServiceError("Compañía no encontrada en inventario", 404)
        else:
            raise DownstreamServiceError(f"Error en el servicio de inventario (HTTP {res.status_code})", 502)
    except requests.exceptions.RequestException as e:
        raise DownstreamServiceError("El servicio de inventario no está disponible o no responde", 503)
