# EXAMEN FINAL — DOCUMENTACIÓN DE INTEGRACIÓN
## Proyecto: PDV Restaurante

---

### Sección 1 — Despliegue en AWS

**1.1 URLs en producción**
- Mi módulo (Inventory/Sales/Purchases): `172.31.30.57:5000` (IP Privada / AWS)
- Mi módulo (Swagger): `http://54.167.127.197:5143/swagger` (Inventory)
- Mi módulo (Swagger): `http://54.167.127.197:5074/swagger` (Sales)
- Mi módulo (Swagger): `http://54.167.127.197:5085/swagger` (Purchases)
- Henrry Coronado (módulo Inventario): `http://98.89.24.229:5143/swagger/index.html`
- Jean Paul Cabrera (módulo Ventas): `http://3.144.161.11:5074/swagger/index.html`

**1.2 Variables de entorno (.env.example)**
```bash
# Conectividad BD
DB_CONNECTION_STRING=Host=postgres-db;Database=sistemagestion;Username=admin;Password=secret_password

# Integración Dinámica
INVENTORY_API_URL=http://inventory-api:5143
```

**1.3 Cómo simular caída de Inventario**
1. Editar el archivo `.env` o el `docker-compose.yml` en el servicio de **Sales.Api**.
2. Cambiar `INVENTORY_API_URL` a una URL inválida (ej: `http://servicio-caido:9999`).
3. Reiniciar el contenedor: `docker compose up -d sale-api`.
4. Intentar agregar un producto al ticket; el Circuit Breaker se activará tras 5 fallos.

---

### Sección 2 — Notificación de restock (SSE)

**2.1 Endpoint SSE en Inventario**
`Inventory.Api/routes/inventory.py` · método `inventory_restock_events`
```python
@bp.route('/api/inventory/companies/<company_cen>/restock-events', methods=['GET'])
def inventory_restock_events(company_cen):
    def event_stream():
        q = queue.Queue()
        with restock_lock:
            restock_queues.append(q)
        try:
            while True:
                event = q.get() # Bloquea hasta que llega un evento
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            with restock_lock:
                restock_queues.remove(q)

    return Response(event_stream(), mimetype="text/event-stream")
```

**2.2 Sistema de Broadcasting (Registro Global)**
`Inventory.Api/routes/inventory.py` · Implementación de hilos y colas
```python
restock_lock = threading.Lock()
restock_queues = []

def broadcast_restock(product_name, quantity, company_cen):
    event_data = {
        'productName': product_name,
        'quantity': quantity,
        'companyCen': company_cen,
        'timestamp': datetime.datetime.now().isoformat()
    }
    with restock_lock:
        for q in restock_queues:
            q.put(event_data)
```

**2.3 Consumidor en Ventas (Frontend)**
`frontend/src/api.js` (Estructura lógica del EventSource)
```javascript
const source = new EventSource(`${INVENTORY_URL}/api/inventory/companies/${companyCen}/restock-events`);
source.onmessage = (e) => {
    const data = JSON.parse(e.data);
    toast.info(`¡RESTOCK! ${data.productName} +${data.quantity} unidades`);
};
```

**2.4 Captura: notificación visible en Ventas**
`[IMAGEN_RESTOCK_NOTIFICATION]`

---

### Sección 3 — Resiliencia con Polly (Adaptado a Python)

**3.1 Política implementada (Retry + Circuit Breaker)**
`Sales.Api/inventory_client.py`
```python
# Retry Policy con urllib3
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])

# Circuit Breaker Manual
circuit_open_until = 0
FAILURE_THRESHOLD = 5

def check_circuit():
    if circuit_open_until > time.time():
        # FALLBACK: Lanzar error controlado
        raise DownstreamServiceError("Servicio deshabilitado (Circuit Breaker)", 503)
```

**3.2 Dónde se aplica**
`Sales.Api/routes/sales.py` · método `sales_pay_ticket`
```python
@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/payment', methods=['POST'])
def sales_pay_ticket(company_cen, ticket_cen):
    # ... lógica local ...
    from inventory_client import consume_stock
    # La llamada está protegida por la política de resiliencia
    consume_stock(company_cen, items) 
```

**3.3 Respuesta cuando Inventario no responde**
```json
{
  "error": "Servicio temporalmente deshabilitado (Circuit Breaker)"
}
```

**3.4 Captura: comportamiento con Inventario caído**
`[IMAGEN_RESILIENCIA_POLLY]`

---

### Sección 4 — Historial y dashboard (Inmutabilidad)

**4.1 Modelo de la tabla de ventas**
`database/init.sql` · Estructura con `precio_unitario`
```sql
CREATE TABLE ventas.ticket_items (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES ventas.tickets(id),
    producto_id INTEGER REFERENCES public.productos(id),
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC(10,2) NOT NULL, -- PRECIO CONGELADO AQUÍ
    subtotal NUMERIC(10,2) NOT NULL
);
```

**4.2 Cómo se guarda el precio en la transacción**
`Sales.Api/routes/sales.py` · método `sales_add_ticket_item`
```python
prod = ensure_local_product(company_cen, p_cen)
# PRECIO INMUTABLE: Se captura el precio del catálogo EN EL MOMENTO de la venta
execute('''
    INSERT INTO ticket_items (ticket_id, producto_id, cantidad, precio_unitario, subtotal)
    VALUES (%s, %s, %s, %s, %s)
''', (t['id'], prod['id'], qty, prod['precio'], float(prod['precio']) * qty))
```

**4.3 Query del dashboard mensual**
`Sales.Api/routes/sales.py` · método `sales_monthly_dashboard`
```python
# SQL que usa los precios históricos de la tabla ticket_items
curr = query("SELECT SUM(total) as total FROM tickets WHERE pagado_en::date >= date_trunc('month', now())")
prev = query("SELECT SUM(total) as total FROM tickets WHERE pagado_en::date < date_trunc('month', now()) ...")
```

**4.4 Captura: dashboard mes actual vs. mes anterior**
`[IMAGEN_DASHBOARD_HISTORIAL]`

---

### Sección 5 — Swagger y Contrato API

URL del Swagger de cada módulo:

| Módulo | URL Swagger |
|---|---|
| Inventario | `http://98.89.24.229:5143/swagger` |
| Ventas | `http://3.144.161.11:5074/swagger` |
| Compras | `http://54.167.127.197:5085/swagger` |
