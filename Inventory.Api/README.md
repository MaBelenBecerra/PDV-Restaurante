# Inventory.Api - Módulo de Inventario

API REST para gestión de catálogo de productos, categorías, unidades de medida y control de stock. Este módulo es consumido por el API de Ventas para validar y descontar inventario.

**Puerto:** `5143`

---

## Arquitectura

El módulo de Inventario expone endpoints para:

1. **Gestión de productos** — Crear, actualizar, listar productos
2. **Validación de stock** — Verificar disponibilidad (consumido por Ventas.Api)
3. **Consumo/aumento de stock** — Modificar inventario (consumido por Ventas.Api)

**Componentes principales:**

```
Inventory.Api/
├── app.py                    # Aplicación Flask principal
├── database.py              # Conexión PostgreSQL y utilidades
├── routes/
│   └── inventory.py         # Endpoints: productos, categorías, stock
├── requirements.txt        # Dependencias Python
├── .env.example            # Variables de entorno (plantilla)
└── contrato-api.yaml       # Especificación OpenAPI 3.0
```

---

## Guía Rápida: Levantar desde Cero

### 1. Requisitos Previos

- **Python 3.9+**
- **PostgreSQL 14+** (con la base de datos `pdv_restaurante` ya creada)

### 2. Clonar y Configurar

```bash
# Navegar al directorio del proyecto
cd Inventory.Api

# Crear archivo .env a partir de la plantilla
cp .env.example .env

# Editar .env y verificar credenciales de BD:
# - DB_HOST=localhost
# - DB_PORT=5432
# - DB_NAME=pdv_restaurante
# - DB_USER=postgres
# - DB_PASSWORD=postgres
# - DB_SEARCH_PATH=inventario,public
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
 * Running on http://0.0.0.0:5143
 * Debug mode: on
```

### 6. Verificar que Funciona

Abre en el navegador o Postman:

```
http://localhost:5143/health
```

**Respuesta esperada:**

```json
{
  "status": "ok",
  "service": "inventory-api"
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
| `DB_SEARCH_PATH` | Search path en PostgreSQL | `inventario,public` |

**Importante:** Nunca commitees un archivo `.env` con credenciales reales. Usa `.env.example` como referencia.

---

## Endpoints Principales

### Empresas

```
GET    /api/inventory/companies
GET    /api/inventory/companies/{company_cen}
```

### Productos

```
GET    /api/inventory/companies/{company_cen}/products
POST   /api/inventory/companies/{company_cen}/products
PUT    /api/inventory/companies/{company_cen}/products/{product_cen}
POST   /api/inventory/companies/{company_cen}/products/lookup         ← Usado por Ventas
```

### Stock (Integración con Ventas)

```
GET    /api/inventory/companies/{company_cen}/stock
POST   /api/inventory/companies/{company_cen}/stock/validate         ← Usado por ventas
POST   /api/inventory/companies/{company_cen}/stock/consume          ← Usado por ventas
POST   /api/inventory/companies/{company_cen}/stock/increase
POST   /api/inventory/companies/{company_cen}/stock/adjustments
```

### Categorías

```
GET    /api/inventory/companies/{company_cen}/categories
POST   /api/inventory/companies/{company_cen}/categories
PUT    /api/inventory/companies/{company_cen}/categories/{category_cen}
```

### Unidades de Medida

```
GET    /api/inventory/companies/{company_cen}/units
POST   /api/inventory/companies/{company_cen}/units
PUT    /api/inventory/companies/{company_cen}/units/{unit_cen}
```

---

## Puntos de Integración con Ventas.Api

### Endpoints consumidos por Ventas:

#### POST `/api/inventory/companies/{company_cen}/products/lookup`

**Usado por:** `inventory_client.lookup_products()` en Sales.Api

**Propósito:** Buscar múltiples productos por CEN

**Cuerpo:**

```json
{
  "productCens": ["uuid-1", "uuid-2"]
}
```

**Respuesta:**

```json
[
  {
    "cen": "uuid-1",
    "code": "PROD-001",
    "name": "Agua 500ml",
    "price": 2.50,
    "stock": 100,
    "stationCode": "COCINA"
  }
]
```

**Código:** [inventory.py línea ~512](routes/inventory.py#L512)

---

#### POST `/api/inventory/companies/{company_cen}/stock/validate`

**Usado por:** `inventory_client.validate_stock()` cuando Ventas agrega un item a un ticket

**Propósito:** Verificar si hay stock sin descontar

**Cuerpo:**

```json
{
  "productCen": "uuid-producto",
  "quantity": 2
}
```

**Respuesta (Stock OK):**

```json
{
  "available": true,
  "quantity": 50
}
```

**Respuesta (Sin stock):**

```json
{
  "available": false,
  "quantity": 1
}
```

**Código:** [inventory.py línea ~577](routes/inventory.py#L577)

---

#### POST `/api/inventory/companies/{company_cen}/stock/consume`

**Usado por:** `inventory_client.consume_stock()` cuando Ventas procesa el PAGO

**Propósito:** Descontar stock (punto crítico de integración)

**Cuerpo:**

```json
{
  "productCen": "uuid-producto",
  "quantity": 2,
  "reference": "SALES",
  "notes": "Ticket TIC-00123 pago efectivo"
}
```

**Respuesta (Éxito):**

```json
{
  "message": "Stock consumed successfully",
  "newStock": 98
}
```

**Respuesta (Error 404 - Producto no existe):**

```json
{
  "error": "Product not found"
}
```

**Respuesta (Error 409 - Sin stock):**

```json
{
  "error": "Insufficient stock"
}
```

**Código:** [inventory.py línea ~598](routes/inventory.py#L598)

---

## Ejemplo de Uso (cURL)

### 1. Listar stock

```bash
curl -X GET http://localhost:5143/api/inventory/companies/550e8400-e29b-41d4-a716-446655440000/stock \
  -H "Content-Type: application/json"
```

**Respuesta:**

```json
[
  {
    "productCen": "uuid-1",
    "productCode": "AGUA500",
    "quantity": 100,
    "minQuantity": 5,
    "lowStock": false
  }
]
```

### 2. Validar stock (como lo hace Ventas)

```bash
curl -X POST http://localhost:5143/api/inventory/companies/550e8400-e29b-41d4-a716-446655440000/stock/validate \
  -H "Content-Type: application/json" \
  -d '{"productCen": "uuid-1", "quantity": 2}'
```

**Respuesta:**

```json
{
  "available": true,
  "quantity": 100
}
```

### 3. Consumir stock (como lo hace Ventas al pagar)

```bash
curl -X POST http://localhost:5143/api/inventory/companies/550e8400-e29b-41d4-a716-446655440000/stock/consume \
  -H "Content-Type: application/json" \
  -d '{"productCen": "uuid-1", "quantity": 2, "reference": "SALES", "notes": "Ticket TIC-001"}'
```

**Respuesta:**

```json
{
  "message": "Stock consumed successfully",
  "newStock": 98
}
```

---

## Desarrollo

### Estructura de rutas (routes/inventory.py)

El archivo `inventory.py` está organizado en secciones:

- **1. COMPANIES ENDPOINTS**
- **2. CATEGORIES ENDPOINTS**
- **3. UNITS ENDPOINTS**
- **4. PRODUCTS ENDPOINTS** (CRUD + lookup)
- **5. STOCK ENDPOINTS** (Validación, consumo, ajustes)
- **6. DASHBOARD ENDPOINTS**

### Patrón de endpoints

Todos los endpoints siguen el mismo patrón:

```python
@bp.route('/api/inventory/companies/<company_cen>/products', methods=['POST'])
def create_product(company_cen):
    try:
        c = get_company(company_cen)  # Valida empresa
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        # Lógica del endpoint
        
        return jsonify({...}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
```

---

## Modelo de Datos

### Productos

```
┌─────────────────┐
│   productos     │
├─────────────────┤
│ id (PK)         │
│ cen (GUID)      │
│ code            │
│ nombre          │
│ precio          │
│ stock           │
│ categoria_id (FK)
│ unidad_id (FK)  │
│ activo          │
└─────────────────┘
```

### Ajustes de Stock

```
┌──────────────────────┐
│  ajustes_stock       │
├──────────────────────┤
│ id (PK)              │
│ producto_id (FK)     │
│ tipo (entrada/salida)│
│ cantidad             │
│ motivo               │
│ creado_en            │
└──────────────────────┘
```

---

## Consideraciones de Diseño

### Estrategia de Validación

El sistema utiliza **dos endpoints separados** para máxima flexibilidad:

1. **Validación (sin efecto)** — `/stock/validate`  
   Verifica disponibilidad sin modificar nada
   Permite que Ventas verifique disponibilidad antes de confirmar

2. **Consumo (irreversible)** — `/stock/consume`  
   Descuenta stock inmediatamente
   Invocado solo en el punto de pago

**Ventaja:** Separa concernimientos y permite reintentos de validación.

### Manejo de Errores

- **404** — Producto no encontrado (sin stock, no desacenta nada)
- **409** — Conflicto: stock insuficiente (sin stock, no desacenta nada)
- **200** — Consumo exitoso

---

## Auditoría y Trazabilidad

Cada consumo de stock genera un registro en la tabla `ajustes_stock`:

```sql
INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en)
VALUES (1, 'salida', 2, 'Ticket pago efectivo', CURRENT_TIMESTAMP)
```

Esto permite auditar todas las modificaciones de stock.

---

## Troubleshooting

### "Product not found" en `/stock/consume`

**Causas:**

1. El `productCen` no existe en la BD
2. El producto fue eliminado

**Solución:** Verifica que el producto existe:

```bash
curl -X GET http://localhost:5143/api/inventory/companies/{company_cen}/products
```

### "Insufficient stock" en `/stock/consume`

Este es el comportamiento esperado cuando no hay suficiente stock.

**Nota:** Ventas.Api valida con `/stock/validate` ANTES de procesar el pago, así que este error no debería ocurrir en flujo normal.

---

## Flowchart: Integración Stock

```
Sales.Api (POST /tickets/{ticket_cen}/items)
    ↓
validate_stock(company_cen, product_cen, qty)
    ↓
    ├─→ POST /api/inventory/stock/validate
    ├─→ if available=true → Agregar item
    └─→ if available=false → Error 400

Sales.Api (POST /tickets/{ticket_cen}/payment)
    ↓
for each item in ticket:
    consume_stock(company_cen, product_cen, qty)
        ↓
        ├─→ POST /api/inventory/stock/consume
        ├─→ if success → actualizar stock
        └─→ if error → Error 400, no desacenta nada
```

---

## Documentación Completa

- **[contrato-api.yaml](contrato-api.yaml)** — Especificación OpenAPI 3.0 completa
- **[RECUPERATORIO.md](../RECUPERATORIO.md)** — Documento de entrega del recuperatorio

---

## Licencia

Este código es parte del Recuperatorio de Integración Inventario ↔ Ventas.
