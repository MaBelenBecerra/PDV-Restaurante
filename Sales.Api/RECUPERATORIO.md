# RECUPERATORIO — Integración Inventario ↔ Ventas

**Estudiante:** Maria Belen Becerra  
**Fecha de entrega:** 30/05/2026  
**Modulo:** Sales.Api (Ventas)  
**Compañero (Inventario.Api):** Jean Paul en teoria

---

## 3.1 — Estructura del Proyecto

### Árbol de carpetas de Sales.Api

```
Sales.Api/
├── app.py                    # Punto de entrada: aplicación Flask
├── database.py              # Capa de datos: conexión a PostgreSQL
├── inventory_client.py      # Cliente HTTP para integración con Inventory.Api 
├── routes/
│   └── sales.py            # Endpoints: tickets, items, pagos, KDS
├── __pycache__/            # Caché de Python compilado
├── requirements.txt        # Dependencias: Flask, Flask-CORS, psycopg2, requests
├── .env.example            # Plantilla de variables de entorno (incluye INVENTORY_API_URL)
├── .gitignore
├── README.md               # Instrucciones para levantar el proyecto
└── contrato-api.yaml       # Contrato OpenAPI 3.0 (integración)
```

### Flujo de una venta de punta a punta

Cuando un usuario registra una venta en el sistema, el flujo es el siguiente:

1. **Cliente HTTP** hace una solicitud POST a `/api/sales/companies/{company_cen}/tickets/{ticket_cen}/items`  
   Ejemplo: `{"productCen": "uuid-123", "quantity": 2}`

2. **sales_add_ticket_item()** en `routes/sales.py` recibe el request:
   - Valida que el ticket exista y esté abierto
   - Llama a `ensure_local_product()` para sincronizar datos del producto desde Inventory.Api
   - Llama a `inventory_client.validate_stock()` para **verificar stock en Inventario** (HTTP call a Inventory.Api)

3. **Si hay stock**:
   - Inserta el item en la tabla `ticket_items` (sin desacenta stock aún)
   - Recalcula totales del ticket (subtotal + impuesto)
   - Retorna 201 con los detalles del item

4. **Cuando el usuario completa el pago** (POST a `/api/sales/companies/{company_cen}/tickets/{ticket_cen}/payment`):
   - **sales_pay_ticket()** itera sobre todos los items del ticket
   - Para cada item, llama a `inventory_client.consume_stock()` (HTTP call a Inventory.Api)
   - **CONSUME el stock en el Inventario** (resta cantidad)
   - Si todos los consumos son exitosos: marca el ticket como PAGADO
   - Si alguno falla: rechaza el pago (error 400)

**Resumen:** Validación en adición del item → Consumo real en pago. Esto desacopla la reserva de la confirmación.

---

## 3.2 — Integración Técnica

### 3.2.1 — ¿Desde qué clase/método hacés la llamada HTTP al Inventario?

**Respuesta:** Las llamadas HTTP se realizan desde el módulo **`inventory_client.py`**, que define tres funciones principales:

```python
# inventory_client.py (líneas 1-41)

import os
import requests

INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "http://localhost:5143")

def lookup_products(company_cen, product_cens):
    """Busca múltiples productos por CEN. Retorna detalles de precios, nombres, etc."""
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

def validate_stock(company_cen, product_cen, quantity):
    """Valida si hay stock suficiente SIN descontar. Usado antes de agregar item."""
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/validate"
        res = requests.post(url, json={"productCen": product_cen, "quantity": quantity}, timeout=5)
        if res.status_code == 200:
            return res.json().get("available", False)
    except Exception as e:
        print(f"Error in validate_stock: {e}")
    return False

def consume_stock(company_cen, product_cen, quantity, notes="Ticket payment"):
    """Consume (descuenta) stock. Usado cuando se PAGA el ticket."""
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/consume"
        res = requests.post(url, json={
            "productCen": product_cen,
            "quantity": quantity,
            "reference": "SALES",
            "notes": notes
        }, timeout=5)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"Error in consume_stock: {e}")
    return False
```

**Punto clave de integración:** Estas funciones son **invocadas desde** `routes/sales.py`:

- `validate_stock()` es llamado en **`sales_add_ticket_item()`** (línea ~212)
- `consume_stock()` es llamado en **`sales_pay_ticket()`** (línea ~387)

---

### 3.2.2 — ¿Cómo está configurada la URL del Inventario? ¿Dónde se define?

**Respuesta:** La URL se externaliza en **variable de entorno** y se lee en `inventory_client.py`:

**Definición en `.env.example`:**

```env
# ==========================================
# INTEGRACIÓN CON INVENTARIO.API
# ==========================================
# URL base del servicio de Inventario
# Esta URL es usada por inventory_client.py para llamadas HTTP
# Ejemplo local: http://localhost:5143
# Ejemplo producción: http://inventory-api.restaurant.com:5143
INVENTORY_API_URL=http://localhost:5143
```

**Lectura en `inventory_client.py` (línea 3):**

```python
INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "http://localhost:5143")
```

**Flujo de configuración:**

1. Durante deployment, se copia `.env.example` → `.env`
2. Se edita `.env` con las credenciales reales
3. Flask carga automáticamente variables desde `.env` (si usa `python-dotenv`)
4. `inventory_client.py` lee `INVENTORY_API_URL` en tiempo de ejecución

**Ventaja:** La URL **no está hardcodeada**. Es fácil cambiar de entorno (dev → producción) solo editando `.env`.

---

### 3.2.3 — ¿Qué pasa si el Inventario devuelve un error 404 o 500?

**Escenario 1: Error 404 (Producto no encontrado)**

**Código en `inventory_client.py`:**

```python
def validate_stock(company_cen, product_cen, quantity):
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/validate"
        res = requests.post(url, json={"productCen": product_cen, "quantity": quantity}, timeout=5)
        if res.status_code == 200:
            return res.json().get("available", False)
    except Exception as e:
        print(f"Error in validate_stock: {e}")
    return False  # Retorna False si no es 200
```

**Comportamiento en `routes/sales.py` (línea ~212):**

```python
has_stock = validate_stock(company_cen, product_cen, qty)
if not has_stock:
    return jsonify({'error': 'Stock insuficiente en inventario'}), 400
```

**Resultado:** El cliente recibe un `400 Bad Request` con mensaje `"Stock insuficiente en inventario"`.

---

**Escenario 2: Error 500 (Servidor Inventario caído)**

**Código en `inventory_client.py`:**

```python
try:
    # ... solicitud HTTP ...
    if res.status_code == 200:
        return res.json().get("available", False)
except Exception as e:  # Captura timeout, conexión rechazada, etc.
    print(f"Error in validate_stock: {e}")
return False  # Retorna False en cualquier error
```

**Comportamiento:**

- Si el puerto 5143 no responde → Timeout (5 segundos) → Excepción capturada → Retorna `False`
- El cliente recibe `400 "Stock insuficiente en inventario"`

**Problema de diseño:** No diferenciamos entre "sin stock" y "servidor caído". Ambos resultan en el mismo error.

**Comportamiento actual del sistema:**

| Caso | HTTP a Inventario | Respuesta a Cliente |
|------|------------------|-------------------|
| 200 + stock OK | 200 + `available: true` | 201 item agregado ✅ |
| 200 + sin stock | 200 + `available: false` | 400 sin stock |
| 404 producto | 404 | 400 sin stock (impreciso) |
| 500 servidor | 500 | 400 sin stock (impreciso) |
| Timeout | Exception | 400 sin stock (impreciso) |

---

## 3.3 — Preguntas Teóricas

### Pregunta A — Cambio en el Contrato: Campo "cantidad" → "qty"

**Pregunta:** Tu compañero te avisa que va a renombrar el campo `"cantidad"` por `"qty"` en la respuesta del endpoint de stock. Tu sistema ya consume ese endpoint. ¿Qué riesgos genera ese cambio? ¿Qué prácticas usarías para que ese cambio no rompa tu sistema?

**Respuesta:**

**Riesgos del cambio:**

El endpoint `/api/inventory/stock/validate` retorna actualmente:

```json
{
  "available": true,
  "cantidad": 10   // Campo que cambiaría a "qty"
}
```

En `inventory_client.py`, accedemos a este campo implícitamente (aunque en este caso no lo extraemos específicamente). Sin embargo, **si cambia el nombre**, cualquier código que acceda a `response['cantidad']` se rompería inmediatamente en producción con `KeyError`.

**Riesgos específicos:**

1. **Error en tiempo de ejecución** — Acceso a clave inexistente causaría crash
2. **Silent failures** — Si el campo se usa con `.get('cantidad', 0)`, retornaría 0 incorrectamente
3. **Inconsistencia entre ambas APIs** — Inventory usa `"cantidad"`, Ventas espera ese nombre

**Prácticas para evitar ruptura (implementaría así):**

**1. Versionado de API:**

```yaml
# En contrato-api.yaml:
/api/inventory/v1/stock/validate:  # Versión 1
  responses:
    '200':
      properties:
        quantity:  # Nombre "definitivo"

# Si cambio: crear v2
/api/inventory/v2/stock/validate:
  responses:
    '200':
      properties:
        qty:  # Nuevo nombre
```

Sales.Api seguiría usando `v1` hasta que actualice su código.

**2. Defensive coding en `inventory_client.py`:**

```python
def validate_stock(company_cen, product_cen, quantity):
    try:
        # ...
        res = requests.post(url, json={...}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            # Para soportar AMBOS nombres (cantidad y qty)
            available = data.get("available", False)
            qty = data.get("qty") or data.get("cantidad", 0)
            return available
    except Exception as e:
        print(f"Error: {e}")
    return False
```

**3. Tests de integración:**

Incluiría un test que verifica la respuesta exacta:

```python
def test_stock_validate_response_structure():
    resp = validate_stock(company_cen, product_cen, 2)
    # Verifica que tenga los campos esperados
    assert 'available' in resp
    assert 'quantity' in resp or 'qty' in resp
```

**4. Contract Testing:**

Usar herramientas como **Pact** o **Swagger UI** para validar que ambos APIs respetan el contrato OpenAPI (`contrato-api.yaml`). Si el compañero cambia un campo, el test fallaría **antes** de desplegar.

**Conclusión:** El riesgo es alto porque es un cambio **breaking**. Se evita con versionado, defensive coding, y testing de contrato.

---

### Pregunta B — Red Caída a Mitad de una Transacción

**Pregunta:** Tu sistema de Ventas llama al Inventario para descontar stock. La red se cae justo después de que Inventario procesó el descuento, pero antes de que la respuesta llegue a Ventas. ¿Qué problema se genera? ¿Cómo lo detectarías? ¿Cómo lo manejarías?

**Respuesta:**

**Problema generado (Pérdida de transaccionalidad):**

Este es el **problema de dos fases distribuido**:

1. Ventas hace POST a `/api/inventory/stock/consume` para descontar 2 unidades
2. Inventory.Api recibe el request, actualiza la BD: `stock = stock - 2`
3. Pero la respuesta HTTP nunca llega a Ventas (red cae, timeout)
4. Ventas interpreta como "error" y **no marca el ticket como PAGADO**
5. **Resultado:** Stock descuentado en Inventario, pero ticket no registrado en Ventas

**Estado inconsistente:**
```
Inventory.Api (BD):  stock = 98  (descuentado)
Sales.Api (BD):      ticket.estado = 'abierto'  (aún abierto)
```

**Cómo detectarlo:**

**1. Logs de diferencia:**

Comparar registros en `ajustes_stock` (Inventory) vs `tickets` pagados (Ventas):

```sql
-- Productos que se descontaron en Inventory pero NO tienen ticket pagado en Ventas
SELECT p.nombre, COUNT(*) as descuentos
FROM ajustes_stock a
JOIN productos p ON a.producto_id = p.id
LEFT JOIN tickets t ON t.pagado_en IS NOT NULL
WHERE a.creado_en > NOW() - INTERVAL '1 hour'
GROUP BY p.id
-- Si hay registros, hay descuentos sin pago registrado
```

**2. Monitoreo de latencia:**

En `sales_pay_ticket()`, agregar logging:

```python
import time
start = time.time()
success = consume_stock(company_cen, item['product_cen'], item['cantidad'])
elapsed = time.time() - start
if elapsed > 5:  # timeout + latencia
    logger.warning(f"Slow stock consume: {elapsed}s")
```

**3. Heartbeat/Polling:**

Sales.Api podría reintentar si la respuesta tarda > 5 segundos:

```python
max_retries = 3
for retry in range(max_retries):
    try:
        response = requests.post(url, timeout=5)
        if response.ok:
            return True
    except requests.Timeout:
        logger.warning(f"Timeout attempt {retry+1}/{max_retries}")
        time.sleep(1)
return False
```

**Cómo manejarlo (soluciones arquitectónicas):**

**Opción 1: Idempotencia con referencia única**

```python
# Generar un ID único para esta transacción
transaction_id = str(uuid.uuid4())

# Enviar a Inventory con transaction_id
consume_stock(
    company_cen, product_cen, quantity,
    reference=f"SALES-{transaction_id}"  # ← Hace idempotente
)

# Si se reintenta, Inventory ve el mismo reference y no descuenta dos veces
```

**Opción 2: Compensating Transactions (Saga Pattern)**

```python
# Si consume_stock falla o tarda mucho:
paid = False
consumed_items = []

for item in items:
    try:
        success = consume_stock(...)
        if success:
            consumed_items.append(item)
    except:
        # Revertir lo ya consumido
        for consumed in consumed_items:
            revert_stock(company_cen, consumed['product_cen'], consumed['qty'])
        raise  # Rechazar pago
```

**Opción 3: Event Sourcing + Dead Letter Queue**

Registrar todas las operaciones en una cola:

```
1. Event: "PaymentInitiated" → Cola
2. Try consume_stock()
3. If success: Event "StockConsumed"
4. If fail/timeout: Dead Letter Queue
5. Admin revisa cola y reconcilia manualmente
```

**Lo que haría en este proyecto:**

Implementaría **Opción 1 (Idempotencia)** porque es simple:

```python
# En inventory_client.py
def consume_stock(company_cen, product_cen, quantity, transaction_id=None):
    if not transaction_id:
        transaction_id = str(uuid.uuid4())
    
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/consume"
        res = requests.post(url, json={
            "productCen": product_cen,
            "quantity": quantity,
            "reference": f"SALES-{transaction_id}",  # ← Idempotencia
            "notes": "Ticket payment"
        }, timeout=5)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"Error: {e}")
    return False
```

**Conclusión:** Es un problema inherente de arquitecturas distribuidas. Se resuelve con idempotencia o sagas distribuidas.

---

### Pregunta C — Inventario Completamente Caído

**Pregunta:** Si el Inventario del compañero está caído completamente, ¿debería tu módulo de Ventas seguir permitiendo registrar ventas o rechazarlas? Justificá considerando ventajas y desventajas de cada postura. ¿Qué hace tu sistema hoy?

**Respuesta:**

**Postura 1: RECHAZAR ventas si Inventario no responde**

**Implementación actual de mi sistema:**

```python
# En sales_add_ticket_item() (routes/sales.py línea ~212)
has_stock = validate_stock(company_cen, product_cen, qty)
if not has_stock:
    return jsonify({'error': 'Stock insuficiente en inventario'}), 400
```

Si Inventory.Api está caído, `validate_stock()` retorna `False` → error 400 → **ventas rechazadas**.

**Ventajas:**
- Garantiza **no vender productos sin stock**
- Evita inconsistencias masivas
- Fuerza al negocio a reparar Inventory.Api rápidamente
- Mejor auditoría: "El sistema no permitió vender"

**Desventajas:**
- **Pérdida de ingresos** durante caída de Inventario
- Mala experiencia de usuario: "Sistema caído, no puedo vender"
- Dependencia fuerte entre microservicios (baja resiliencia)

---

**Postura 2: PERMITIR ventas si Inventario no responde (Fail Open)**

**Implementación alternativa:**

```python
has_stock = validate_stock(company_cen, product_cen, qty)
if has_stock is None:  # Null = no respuesta
    logger.warning(f"Inventory unreachable, allowing sale anyway")
    has_stock = True  # Confiar en stock anterior

if not has_stock:
    return jsonify({'error': 'Stock insuficiente'}), 400
```

**Ventajas:**
- **Continuidad de negocio** durante caída de Inventory
- Los ingresos no se pierden
- Mejor UX: usuario no sabe que hay problema
- Mayor resiliencia arquitectónica

**Desventajas:**
- Riesgo de **sobrevender** masivamente
- Después habrá pedidos sin costo es decir clientes a los que se vendió lo que no hay
- Recuperación compleja: ¿quién revierte las ventas?
- Auditoría difícil: "Vendimos sin verificar"

---

**Análisis de negocio:**

Para un restaurante PDV:

- **Caída de 5 minutos** Postura 2 (permitir) hace más sentido: pierdo 5 min de ventas
- **Caída de 1 hora** Postura 1 (rechazar) hace más sentido: mejor parar que sobrevender

**Opción 3: HIBRIDA (Graceful Degradation)**

```python
# Intentar validar con timeout corto
try:
    has_stock = validate_stock(..., timeout=2)
except Timeout:
    # Inventory tarda, pero confiar en cache local
    local_stock = get_cached_inventory()
    has_stock = local_stock[product_cen] >= qty
    logger.warning(f"Using cached inventory due to timeout")
```

Almacenar último estado conocido del inventario en caché local. Si falla Inventory, usa caché (que tiene ~1 hora de antigüedad máximo).

---

**Recomendación final:**

Para este recuperatorio, implemento **Postura 1 (RECHAZAR)** porque:
1. Es la actual
2. Es correcta para un entorno de prueba
3. Garantiza integridad de datos
4. Es pedagógico: enseña importancia de integración

Pero en **producción**, usaría **Opción 3 (Caché)** porque:
- Los restaurantes no pueden dejar de vender por caída de un microservicio
- Caché de 1 hora es aceptable
- Reconciliación posterior si hay inconsistencia

---

### Pregunta D — URL Hardcodeada vs. Variable de Entorno

**Pregunta:** ¿Por qué tener la URL del compañero escrita directamente en el código como `"http://localhost:5143"` es un problema? ¿Cómo lo resolviste en tu proyecto?

**Respuesta:**

**Problemas de hardcoding:**

1. **No es portable**
   ```python
   # Hardcodeado
   INVENTORY_URL = "http://localhost:5143"
   
   # Si despliego en producción en servidor 192.168.1.10:
   # Script no funciona
   # Debo editar el código
   # Riesgo de commitear valores de producción
   ```

2. **Seguridad: credenciales expuestas**
   ```python
   # Código
   INVENTORY_URL = "http://user:password@inventory.prod.com:5143"
   
   # Se guarda en repositorio público
   # Cualquiera ve las credenciales
   ```

3. **Dificultad de testing**
   ```python
   # Hardcodeado no permite tests
   def validate_stock(...):
       res = requests.post("http://localhost:5143/...")
       # En tests, no puedo usar mock de otra URL
   ```

4. **Cambios frecuentes**
   ```python
   # Dev: http://localhost:5143
   # Staging: http://staging-inventory.internal:5143
   # Prod: http://inventory.prod.com:5143
   
   # Sin entorno = debo editar código 3 veces
   ```

5. **Accidental commits de valores "temporales"**
   ```python
   # Dev hizo: INVENTORY_URL = "http://192.168.1.5:5143"  # Mi IP local
   # Commitea sin darse cuenta
   # Todos reciben esa IP que no sirve para ellos
   ```

---

**Cómo lo resolví en el proyecto:**

**1. Variables de Entorno (`.env`)**

`.env.example`:
```env
# INTEGRACIÓN CON INVENTARIO.API
INVENTORY_API_URL=http://localhost:5143
```

**2. Lectura en tiempo de ejecución (`inventory_client.py`)**

```python
import os

INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "http://localhost:5143")                                                      
#          Lee desde variable              Valor por defecto (dev)

def validate_stock(company_cen, product_cen, quantity):
    url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/validate"
    # ... usa la variable, no hardcode
```

**3. Nunca commitear `.env` (usar `.gitignore`)**

```bash
# En .gitignore
.env
*.pem
*.key
```

**4. Cada entorno tiene su `.env`**

```bash
# Desarrollo
.env contiene: INVENTORY_API_URL=http://localhost:5143

# Staging
.env contiene: INVENTORY_API_URL=http://staging-inventory.internal:5143

# Producción
.env contiene: INVENTORY_API_URL=http://inventory.prod.com:5143
```

**5. Docker / CI/CD inyecta valores en tiempo de despliegue**

```dockerfile
# Dockerfile
ENV INVENTORY_API_URL=${INVENTORY_API_URL}

# O en CI/CD (GitHub Actions)
- name: Deploy
  env:
    INVENTORY_API_URL: http://inventory.prod.com:5143
  run: python app.py
```

---

**Comparación antes vs. después:**

| Aspecto | Hardcodeado | Env var |
|--------|----------------|----------|
| Cambiar URL | Editar código + git commit | Solo .env |
| Seguridad | Credenciales en repo | Credenciales locales |
| Testing | Imposible mockear | Fácil mockear |
| Deploy multi-env | Múltiples branches | Un solo código |
| Accidental commits | Frecuente | Casi imposible |

---

**Código actual del proyecto:**

**`inventory_client.py`:**
```python
import os
import requests

INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "http://localhost:5143")

def validate_stock(company_cen, product_cen, quantity):
    try:
        url = f"{INVENTORY_API_URL}/api/inventory/companies/{company_cen}/stock/validate"
        res = requests.post(url, json={"productCen": product_cen, "quantity": quantity}, timeout=5)
        if res.status_code == 200:
            return res.json().get("available", False)
    except Exception as e:
        print(f"Error in validate_stock: {e}")
    return False
```

**`.env.example`:**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pdv_restaurante
DB_USER=postgres
DB_PASSWORD=postgres
DB_SEARCH_PATH=ventas,inventario,public

# INTEGRACIÓN CON INVENTARIO.API
INVENTORY_API_URL=http://localhost:5143
```

**Conclusión:** Variables de entorno permiten que **el mismo código** funcione en cualquier entorno sin cambios. Es estándar en industria (12-factor app).

---

## Referencias

- **Contrato API:** [contrato-api.yaml](contrato-api.yaml)
- **README Sales.Api:** [README.md](README.md)
- **Archivo de integración:** [inventory_client.py](inventory_client.py)
- **Rutas de endpoints:** [routes/sales.py](routes/sales.py)

