# Sales.Api - Módulo de Ventas

API REST para gestión de tickets (facturas), items de venta y pagos en el sistema PDV Restaurante. Este módulo integra con el API de Inventario para validar y consumir stock de productos.

**Puerto:** `5074`

---

##Arquitectura

El módulo de Ventas se comunica con el API de Inventario mediante llamadas HTTP para:

1. **Validación de stock** — Antes de agregar un item a un ticket, se valida con Inventory.Api
2. **Consumo de stock** — Cuando se completa el pago del ticket, se descuenta el stock en Inventario

**Componentes principales:**

```
Sales.Api/
├── app.py                    # Aplicación Flask principal
├── database.py              # Conexión PostgreSQL y utilidades
├── inventory_client.py      # Cliente HTTP para Inventory.Api (integración)
├── routes/
│   └── sales.py            # Endpoints: tickets, items, pagos
├── requirements.txt        # Dependencias Python
├── .env.example            # Variables de entorno (plantilla)
└── contrato-api.yaml       # Especificación OpenAPI 3.0
```

---

##Guía Rápida: Levantar desde Cero

### 1. Requisitos Previos

- **Python 3.9+**
- **PostgreSQL 14+** (con la base de datos `pdv_restaurante` ya creada)
- **Inventory.Api corriendo en puerto 5143** (necesario para integración)

### 2. Clonar y Configurar

```bash
# Navegar al directorio del proyecto
cd Sales.Api

# Crear archivo .env a partir de la plantilla
cp .env.example .env

# Editar .env y verificar credenciales de BD:
# - DB_HOST=localhost
# - DB_PORT=5432
# - DB_NAME=pdv_restaurante
# - DB_USER=postgres
# - DB_PASSWORD=postgres
# - INVENTORY_API_URL=http://localhost:5143  (URL del Inventory.Api)
```

### 3. Instalar Dependencias

```bash
# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 4. Verificar Base de Datos

Asegúrate de que la base de datos PostgreSQL esté corriendo y contenga el schema del proyecto (ver archivo `database/postgres_schema.sql` en la raíz).

### 5. Levantar el Servidor

```bash
python app.py
```

**Salida esperada:**

```
 * Running on http://0.0.0.0:5074
 * Debug mode: on
```

### 6. Verificar que Funciona

Abre en el navegador o Postman:

```
http://localhost:5074/health
```

**Respuesta esperada:**

```json
{
  "status": "ok",
  "service": "sales-api"
}
```

---

## 📋 Variables de Entorno (.env)

| Variable | Descripción | Ejemplo | Requerida |
|----------|-------------|---------|-----------|
| `DB_HOST` | Host de PostgreSQL | `localhost` |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DB_NAME` | Nombre de la base de datos | `pdv_restaurante` |
| `DB_USER` | Usuario PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña PostgreSQL | `postgres` |
| `DB_SEARCH_PATH` | Search path en PostgreSQL | `ventas,inventario,public` |
| `INVENTORY_API_URL` | URL base del Inventory.Api | `http://localhost:5143` |

**Importante:** Nunca commitees un archivo `.env` con credenciales reales. Usa `.env.example` como referencia.

---

## Endpoints Principales

### Tickets

```
GET    /api/sales/companies/{company_cen}/tickets
POST   /api/sales/companies/{company_cen}/tickets
GET    /api/sales/companies/{company_cen}/tickets/{ticket_cen}
POST   /api/sales/companies/{company_cen}/tickets/{ticket_cen}/cancel
```

### Items (con Validación Inventario)

```
GET    /api/sales/companies/{company_cen}/tickets/{ticket_cen}/items
POST   /api/sales/companies/{company_cen}/tickets/{ticket_cen}/items          ← Valida stock con Inventory.Api
PATCH  /api/sales/companies/{company_cen}/tickets/{ticket_cen}/items/{item_cen}
DELETE /api/sales/companies/{company_cen}/tickets/{ticket_cen}/items/{item_cen}
```

### Pagos (Consumo Stock)

```
POST   /api/sales/companies/{company_cen}/tickets/{ticket_cen}/payment        Consume stock en Inventory.Api
```

---

## Integración con Inventory.Api

### Archivos clave de integración:

- **[inventory_client.py](inventory_client.py)** — Cliente HTTP que encapsula llamadas a Inventory.Api
- **[routes/sales.py](routes/sales.py)** — Lógica de endpoints con llamadas a `inventory_client`

### Flujos de integración:

#### Agregar Item a Ticket (POST `/api/sales/companies/{company_cen}/tickets/{ticket_cen}/items`)

```python
# En sales_add_ticket_item():
from inventory_client import validate_stock

has_stock = validate_stock(company_cen, product_cen, qty)
if not has_stock:
    return {'error': 'Stock insuficiente en inventario'}, 400
    
# Si hay stock, agrega el item al ticket (aún no desacenta stock)
```

**Código:**  
[sales.py línea ~212](routes/sales.py#L212)

#### Procesar Pago (POST `/api/sales/companies/{company_cen}/tickets/{ticket_cen}/payment`)

```python
# En sales_pay_ticket():
from inventory_client import consume_stock

for item in items:
    success = consume_stock(company_cen, item['product_cen'], item['cantidad'])
    if not success:
        return {'error': f"Stock insuficiente para {item['nombre']}"}, 400

# Si todos los consumos son exitosos, marca ticket como PAGADO
```

**Código:**  
[sales.py línea ~385](routes/sales.py#L385)

---

## Ejemplo de Uso (cURL)

### 1. Crear un ticket

```bash
curl -X POST http://localhost:5074/api/sales/companies/550e8400-e29b-41d4-a716-446655440000/tickets \
  -H "Content-Type: application/json" \
  -d '{"mesero": "Juan Pérez"}'
```

**Respuesta:**

```json
{
  "cen": "ticket-uuid-001",
  "ticketNumber": "TIC-00001",
  "status": "OPEN",
  "itemCount": 0,
  "createdAt": "2026-05-30T10:00:00",
  "mesero": "Juan Pérez",
  "total": 0.0
}
```

### 2. Agregar item (valida stock en Inventario)

```bash
curl -X POST http://localhost:5074/api/sales/companies/550e8400-e29b-41d4-a716-446655440000/tickets/ticket-uuid-001/items \
  -H "Content-Type: application/json" \
  -d '{
    "productCen": "product-uuid-001",
    "quantity": 2,
    "notes": "Sin cebolla"
  }'
```

**Respuesta:**

```json
{
  "cen": "item-uuid-001",
  "productCen": "product-uuid-001",
  "quantity": 2,
  "unitPrice": 2.50,
  "notes": "Sin cebolla",
  "ticket_totals": {
    "subtotal": 5.00,
    "impuesto": 0.65,
    "total": 5.65,
    "taxRate": 0.13
  }
}
```

### 3. Pagar ticket (consume stock en Inventario)

```bash
curl -X POST http://localhost:5074/api/sales/companies/550e8400-e29b-41d4-a716-446655440000/tickets/ticket-uuid-001/payment \
  -H "Content-Type: application/json" \
  -d '{"paymentMethod": "CASH", "amount": 5.65}'
```

**Respuesta:**

```json
{
  "paymentCen": "payment-uuid-001",
  "status": "PAID",
  "amount": 5.65
}
```

---

## Manejo de Errores en Integración

### ¿Qué pasa si Inventory.Api no responde?

```python
# En inventory_client.py:
except Exception as e:
    print(f"Error in validate_stock: {e}")
    return False  # Considera sin stock si no hay respuesta
```

**Comportamiento:**

- Si `validate_stock()` falla → No se agrega el item (error 400 al cliente)
- Si `consume_stock()` falla → Se rechaza el pago (error 400 al cliente)

### HTTP Status Codes de Integración

| Caso | Código HTTP |
|------|-----------|
| Stock validado correctamente | 201 (item agregado) |
| Sin stock en Inventario | 400 `Stock insuficiente en inventario` |
| Inventario no responde | 400 `Error de conexión` |
| Producto no existe | 404 `Product not found in inventory` |

---

## Documentación Completa

- **[contrato-api.yaml](contrato-api.yaml)** — Especificación OpenAPI 3.0 completa
- **[RECUPERATORIO.md](../RECUPERATORIO.md)** — Documento de entrega del recuperatorio

---

## Desarrollo

### Estructura de rutas (routes/sales.py)

El archivo `sales.py` está organizado en secciones:

- **1. TICKETS ENDPOINTS** (GET, POST, GET detail, CANCEL)
- **2. COMANDAS & KDS ENDPOINTS** (Kitchen Display System)
- **3. DASHBOARD ENDPOINTS** (Reportes)

### Patrón de endpoints

Todos los endpoints siguen el mismo patrón:

```python
@bp.route('/api/sales/companies/<company_cen>/tickets', methods=['POST'])
def sales_create_ticket(company_cen):
    try:
        c = get_company(company_cen)  # Valida empresa
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        # Lógica del endpoint
        
        return jsonify({...}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
```

---

## Consideraciones de Diseño

### Validación vs. Consumo de Stock

El sistema utiliza **dos endpoints diferentes** en Inventory.Api:

1. **`/stock/validate`** — Verifica sin descontar (cuando se agrega item)
2. **`/stock/consume`** — Descuenta el stock (cuando se paga)

**Ventaja:** Un usuario puede modificar el ticket antes de pagar sin afectar el inventario.

### CEN (Código de Empresa)

Todos los endpoints requieren `company_cen` (GUID único). El sistema auto-crea empresas si no existen.

---

## Troubleshooting

### "Stock insuficiente en inventario" al agregar item

**Causas posibles:**

1. El Inventory.Api no está corriendo
2. El stock en Inventario es realmente insuficiente
3. Variable `INVENTORY_API_URL` en `.env` es incorrecta

**Solución:**

```bash
# Verificar que Inventory.Api esté corriendo
curl http://localhost:5143/health

# Verificar que .env tenga la URL correcta
cat .env | grep INVENTORY_API_URL
```

### "Company not found"

El endpoint creará la empresa automáticamente si no existe. Si sigue sin funcionar, verifica que PostgreSQL esté corriendo.

---

## Licencia

Este código es parte del Recuperatorio de Integración Inventario ↔ Ventas.
