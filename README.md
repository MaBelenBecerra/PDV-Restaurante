# Restaurante PDV

Sistema completo de Punto de Venta (PDV) para restaurantes con frontend interactivo, backend robusto y base de datos SQLite.

## Características

- 🧾 **Gestión de Cuentas**: Crear y administrar múltiples cuentas simultáneamente
- 🛍️ **Catálogo**: Productos organizados por categorías
- 📦 **Inventario**: Control de stock con ajustes manuales
- 👨‍🍳 **KDS Cocina**: Display para estación de cocina (Kitchen Display System)
- 🍸 **KDS Bar**: Display para estación de bar
- 📊 **Dashboard**: Métricas de ventas diarias
- 💳 **Métodos de Pago**: Efectivo, QR, Tarjeta
- 🔧 **Configuración**: Ajuste de tasa de impuesto

## Requisitos

- Python 3.9+
- Node.js 18+

## Instalación y Ejecución

### Backend

```bash
cd backend
pip install flask flask-cors
python app.py
```

El backend se ejecutará en `http://localhost:5000`

Endpoints disponibles:
- `GET /health` - Verificar estado del servidor
- `/api/productos`, `/api/categorias`, `/api/unidades` - Gestión de productos
- `/api/tickets` - Gestión de cuentas/tickets
- `/api/inventario` - Control de stock
- `/api/kds/<estacion_id>` - Kitchen Display System
- `/api/dashboard` - Métricas
- `/api/configuracion` - Configuración del sistema

### Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend se ejecutará en `http://localhost:5173`

## Estructura del Proyecto

```
restaurante/
├── backend/
│   ├── app.py                 # Aplicación Flask principal
│   ├── database.py            # Gestión de base de datos SQLite
│   ├── schema.sql             # Esquema de la base de datos
│   ├── restaurante.db         # Base de datos (se crea automáticamente)
│   └── routes/
│       ├── categorias.py      # Endpoints de categorías
│       ├── unidades.py        # Endpoints de unidades
│       ├── productos.py       # Endpoints de productos
│       ├── inventario.py      # Endpoints de inventario
│       ├── tickets.py         # Endpoints de tickets/cuentas
│       ├── comandas.py        # Endpoints de comandas y KDS
│       └── dashboard.py       # Endpoints de dashboard
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx           # Punto de entrada React
│       ├── App.jsx            # Componente principal con navegación
│       ├── index.css          # Estilos globales
│       ├── api.js             # Cliente API centralizado
│       ├── components/
│       │   ├── Toast.jsx      # Notificaciones
│       │   └── Modal.jsx      # Diálogos
│       └── pages/
│           ├── Dashboard.jsx  # Métricas diarias
│           ├── Catalogo.jsx   # Gestión de productos y configuración
│           ├── Inventario.jsx # Control de stock
│           ├── PDV.jsx        # Sistema de punto de venta
│           └── KDS.jsx        # Kitchen Display System
└── README.md
```

## Primera Ejecución

1. **Backend**: Al iniciar por primera vez, se crea automáticamente la base de datos SQLite con:
   - Tablas de productos, categorías, unidades
   - Tablas de tickets e items
   - Tablas de pagos y comandas
   - Datos iniciales de prueba (8 productos de ejemplo)
   - Vistas para el dashboard

2. **Frontend**: Los datos se descargan automáticamente desde el backend

## Uso

### Dashboard
- Vista rápida de métricas del día
- Top 5 productos vendidos
- Alertas de stock bajo y productos agotados
- Estado de comandas pendientes

### Catálogo
- **Productos**: Crear, editar, activar/desactivar, marcar como agotados
- **Categorías**: Gestión de categorías de productos
- **Unidades**: Definir unidades de medida
- **Configuración**: Ajustar tasa de impuesto (IVA)

### Inventario
- Ver stock de todos los productos
- Badges visuales: OK (verde), BAJO (amarillo), AGOTADO (rojo)
- Registrar entradas y salidas de stock con motivo

### PDV - Punto de Venta
- **Panel izquierdo**: Lista de cuentas abiertas
- **Panel derecho**: Detalle de cuenta seleccionada
  - Búsqueda y filtrado de productos
  - Grid visual de productos con precio y stock
  - Agregar items con cantidad flexible
  - Notas por item (ej: "sin cebolla")
  - Cálculo automático de totales
  - Botones de acciones: Enviar Comanda, Cancelar, Cobrar

### Cocina (KDS)
- Pantalla completa optimizada para cocina
- Cards grandes por ticket
- Items con estado: Pendiente (rojo) → En Preparación (amarillo) → Listo (verde)
- Click en estado para avanzar al siguiente
- Muestra notas especiales
- Actualización automática cada 15 segundos

### Bar (KDS)
- Igual que la cocina pero filtrando items de bebidas

## Datos de Prueba

Se incluyen datos iniciales para pruebas:

**Categorías**: Entradas, Platos principales, Postres, Bebidas, Cócteles

**Productos**:
- Ceviche mixto - $45.00
- Tequeños - $25.00
- Pollo a la brasa - $55.00
- Lomo saltado - $65.00
- Suspiro limeño - $20.00
- Chicha morada - $12.00
- Limonada - $10.00
- Pisco sour - $30.00

## Base de Datos

### Tablas Principales

- **configuracion**: Tasa de impuesto global
- **categorias**: Categorías de productos
- **unidades**: Unidades de medida (porción, vaso, botella, etc.)
- **productos**: Catálogo de productos con precio y stock
- **tickets**: Cuentas/órdenes de clientes
- **ticket_items**: Items dentro de cada ticket
- **ajustes_stock**: Historial de cambios de inventario
- **pagos**: Registro de pagos completados
- **estaciones**: Cocina y Bar
- **comandas**: Órdenes enviadas a estaciones
- **comanda_items**: Items dentro de cada orden

### Triggers

- Cálculo automático de totales (subtotal, impuesto, total)
- Descuento de stock al pagar
- Marcado automático de pagado al registrar pago

### Vistas

- `v_ventas_hoy`: Métricas diarias
- `v_top_productos`: Productos más vendidos
- `v_comandas_estado`: Contadores de estado de comandas

## Reglas de Negocio

- No se puede crear categoría/unidad duplicada
- Precio de producto debe ser mayor a 0
- No se puede agregar producto inactivo o agotado a un ticket
- No se puede pagar ticket vacío
- No se puede pagar si falta stock
- No se puede editar items de ticket pagado
- Salida de inventario no puede dejar stock negativo
- Al pagar se descuenta automáticamente el stock

## Tecnologías

### Backend
- **Flask** - Framework web Python
- **Flask-CORS** - Soporte para CORS
- **SQLite3** - Base de datos local
- **Python 3.9+** - Runtime

### Frontend
- **React 18** - Librería UI
- **Vite** - Build tool y dev server
- **Tailwind CSS** - Framework de estilos
- **Fetch API** - Cliente HTTP (sin dependencias externas)

## Notas de Desarrollo

- Todo el código está listo para producción
- Sin comentarios innecesarios, código limpio y funcional
- Manejo de errores en frontend y backend
- Validaciones de negocio implementadas
- Interfaz responsive y táctil-friendly
- Auto-actualización de datos en vistas críticas (PDV, KDS)

## Licencia

MIT
