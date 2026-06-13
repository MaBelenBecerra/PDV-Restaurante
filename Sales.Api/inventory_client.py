import os
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from dotenv import load_dotenv

load_dotenv()

INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "http://inventory-api:5143")

# Session with RETRY (Polly Pattern 1)
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    raise_on_status=False
)
session.mount('http://', HTTPAdapter(max_retries=retries))

# Simple CIRCUIT BREAKER (Polly Pattern 2)
circuit_open_until = 0
FAILURE_THRESHOLD = 5
failures = 0

class DownstreamServiceError(Exception):
    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code

def check_circuit():
    global circuit_open_until, failures
    if circuit_open_until > time.time():
        # FALLBACK (Polly Pattern 3): Return controlled error when circuit is open
        raise DownstreamServiceError("Servicio temporalmente deshabilitado (Circuit Breaker)", 503)
    return True

def record_failure():
    global failures, circuit_open_until
    failures += 1
    if failures >= FAILURE_THRESHOLD:
        circuit_open_until = time.time() + 30 # Open for 30s
        failures = 0

def record_success():
    global failures
    failures = 0

def lookup_products(company_cen, product_cens):
    check_circuit()
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/products/lookup"
        res = session.post(url, json={"productCens": product_cens}, timeout=5)
        if res.status_code == 200:
            record_success()
            return res.json()
        record_failure()
        return []
    except Exception:
        record_failure()
        # FALLBACK: Return empty list instead of crashing
        return []

def increase_stock(company_cen, items):
    check_circuit()
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/increase"
        res = session.post(url, json={"items": items}, timeout=5)
        if res.status_code in (200, 201):
            record_success()
            return True
        record_failure()
    except Exception:
        record_failure()
    return False

def consume_stock(company_cen, items):
    check_circuit()
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/consume"
        res = session.post(url, json={"items": items}, timeout=5)
        if res.status_code in (200, 201):
            record_success()
            return True
        record_failure()
    except Exception:
        record_failure()
    return False
