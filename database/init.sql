-- ============================================================
-- BASE DE DATOS: PDV-RESTAURANTE (POSTGRESQL INITIALIZATION)
-- ============================================================

-- Crear Esquemas
CREATE SCHEMA IF NOT EXISTS inventario;
CREATE SCHEMA IF NOT EXISTS ventas;
CREATE SCHEMA IF NOT EXISTS compras;

-- ============================================================
-- ESQUEMA: PUBLIC (Compartido Globalmente)
-- ============================================================

-- Empresas
CREATE TABLE IF NOT EXISTS public.empresas (
    id SERIAL PRIMARY KEY,
    cen VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    nit VARCHAR(50) NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ESQUEMA: INVENTARIO (Catálogo y Stock)
-- ============================================================

-- Categorías
CREATE TABLE IF NOT EXISTS inventario.categorias (
    id SERIAL PRIMARY KEY,
    cen VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Unidades
CREATE TABLE IF NOT EXISTS inventario.unidades (
    id SERIAL PRIMARY KEY,
    cen VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Productos
CREATE TABLE IF NOT EXISTS inventario.productos (
    id SERIAL PRIMARY KEY,
    categoria_id INTEGER NOT NULL REFERENCES inventario.categorias(id),
    unidad_id INTEGER NOT NULL REFERENCES inventario.unidades(id),
    nombre VARCHAR(255) NOT NULL,
    precio NUMERIC(10,2) NOT NULL CHECK (precio > 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    agotado INTEGER NOT NULL DEFAULT 0 CHECK (agotado IN (0,1)),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cen VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    station_code VARCHAR(50) DEFAULT 'COCINA'
);

-- Ajustes de Stock (Historias antiguas / Compatibilidad)
CREATE TABLE IF NOT EXISTS inventario.ajustes_stock (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES inventario.productos(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('entrada','salida')),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    motivo TEXT NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Bodegas
CREATE TABLE IF NOT EXISTS inventario.bodegas (
    id SERIAL PRIMARY KEY,
    cen VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Documentos de Inventario
CREATE TABLE IF NOT EXISTS inventario.documentos (
    id SERIAL PRIMARY KEY,
    cen VARCHAR(50) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('ADJUSTMENT','ENTRY','CONSUME')),
    titulo VARCHAR(255),
    referencia VARCHAR(255),
    notas TEXT,
    estado VARCHAR(50) NOT NULL DEFAULT 'CONFIRMED' CHECK (estado IN ('DRAFT','CONFIRMED','CANCELLED')),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmado_en TIMESTAMP
);

-- Items de Documentos de Inventario (Sincronizado con Inventory.Api)
CREATE TABLE IF NOT EXISTS inventario.documentos_items (
    id SERIAL PRIMARY KEY,
    documento_id INTEGER NOT NULL REFERENCES inventario.documentos(id) ON DELETE CASCADE,
    producto_cen VARCHAR(50) NOT NULL,
    cantidad NUMERIC(10,2) NOT NULL,
    costo_unitario NUMERIC(10,2),
    notas TEXT,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Movimientos Kardex (Sincronizado con Inventory.Api)
CREATE TABLE IF NOT EXISTS inventario.kardex (
    id SERIAL PRIMARY KEY,
    movimiento_cen VARCHAR(50) NOT NULL UNIQUE,
    documento_cen VARCHAR(50),
    producto_cen VARCHAR(50) NOT NULL,
    bodega_cen VARCHAR(50) NOT NULL,
    tipo_movimiento VARCHAR(50) NOT NULL,
    cantidad NUMERIC(10,2) NOT NULL,
    costo_unitario NUMERIC(10,2),
    motivo TEXT,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ESQUEMA: VENTAS (Tickets, Pagos y KDS)
-- ============================================================

-- Configuración Global
CREATE TABLE IF NOT EXISTS ventas.configuracion (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    tasa_impuesto NUMERIC(5,2) NOT NULL DEFAULT 0.13,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO ventas.configuracion (id, tasa_impuesto) VALUES (1, 0.13) ON CONFLICT DO NOTHING;

-- Clientes
CREATE TABLE IF NOT EXISTS ventas.clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    telefono VARCHAR(50),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Meseros
CREATE TABLE IF NOT EXISTS ventas.meseros (
    id SERIAL PRIMARY KEY,
    cen VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefono VARCHAR(50),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tickets
CREATE TABLE IF NOT EXISTS ventas.tickets (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES ventas.clientes(id),
    mesero VARCHAR(255) NOT NULL,
    estado VARCHAR(50) NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto','pagado','cancelado')),
    subtotal NUMERIC(10,2) NOT NULL DEFAULT 0,
    impuesto NUMERIC(10,2) NOT NULL DEFAULT 0,
    total NUMERIC(10,2) NOT NULL DEFAULT 0,
    tasa_impuesto NUMERIC(5,2) NOT NULL DEFAULT 0.13,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pagado_en TIMESTAMP,
    cen VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    table_code VARCHAR(50),
    vendor_cen VARCHAR(50)
);

-- Ticket Items
CREATE TABLE IF NOT EXISTS ventas.ticket_items (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES ventas.tickets(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES inventario.productos(id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario > 0),
    subtotal NUMERIC(10,2) NOT NULL,
    nota TEXT DEFAULT '',
    cen VARCHAR(50) NOT NULL UNIQUE
);

-- Pagos
CREATE TABLE IF NOT EXISTS ventas.pagos (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL UNIQUE REFERENCES ventas.tickets(id) ON DELETE CASCADE,
    metodo VARCHAR(50) NOT NULL CHECK (metodo IN ('efectivo','qr','tarjeta')),
    monto NUMERIC(10,2) NOT NULL CHECK (monto > 0),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cen VARCHAR(50) NOT NULL UNIQUE
);

-- Estaciones KDS
CREATE TABLE IF NOT EXISTS ventas.estaciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('cocina','bar')),
    cen VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE
);

-- Comandas KDS
CREATE TABLE IF NOT EXISTS ventas.comandas (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES ventas.tickets(id) ON DELETE CASCADE,
    estacion_id INTEGER NOT NULL REFERENCES ventas.estaciones(id),
    nro_comanda VARCHAR(50) NOT NULL UNIQUE,
    estado VARCHAR(50) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','en_preparacion','listo','sent')),
    es_reenvio INTEGER NOT NULL DEFAULT 0 CHECK (es_reenvio IN (0,1)),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cen VARCHAR(50) NOT NULL UNIQUE
);

-- Comanda Items KDS
CREATE TABLE IF NOT EXISTS ventas.comanda_items (
    id SERIAL PRIMARY KEY,
    comanda_id INTEGER NOT NULL REFERENCES ventas.comandas(id) ON DELETE CASCADE,
    ticket_item_id INTEGER NOT NULL REFERENCES ventas.ticket_items(id) ON DELETE CASCADE,
    estado VARCHAR(50) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','en_preparacion','listo')),
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cen VARCHAR(50) NOT NULL UNIQUE
);

-- ============================================================
-- ESQUEMA: COMPRAS (Proveedores y Abastecimiento)
-- ============================================================

-- Proveedores
CREATE TABLE IF NOT EXISTS compras.proveedores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    contacto VARCHAR(255),
    telefono VARCHAR(50),
    email VARCHAR(100),
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cen VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE
);

-- Compras
CREATE TABLE IF NOT EXISTS compras.compras (
    id SERIAL PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES compras.proveedores(id),
    estado VARCHAR(50) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','confirmada','cancelada')),
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total NUMERIC(10,2) NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmado_en TIMESTAMP,
    cen VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE
);

-- Compra Items
CREATE TABLE IF NOT EXISTS compras.compra_items (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES compras.compras(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES inventario.productos(id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario > 0),
    subtotal NUMERIC(10,2) NOT NULL,
    cen VARCHAR(50) NOT NULL UNIQUE
);

-- ============================================================
-- TRIGGERS DE TOTALES AUTOMATICOS (PL/pgSQL en VENTAS)
-- ============================================================

CREATE OR REPLACE FUNCTION ventas.update_ticket_totals() RETURNS TRIGGER AS $$
DECLARE
    t_id INTEGER;
    t_rate NUMERIC;
BEGIN
    IF TG_OP = 'DELETE' THEN
        t_id := OLD.ticket_id;
    ELSE
        t_id := NEW.ticket_id;
    END IF;

    SELECT tasa_impuesto INTO t_rate FROM ventas.tickets WHERE id = t_id;

    UPDATE ventas.tickets SET
        subtotal = COALESCE((SELECT SUM(subtotal) FROM ventas.ticket_items WHERE ticket_id = t_id), 0),
        impuesto = COALESCE((SELECT SUM(subtotal) FROM ventas.ticket_items WHERE ticket_id = t_id), 0) * t_rate,
        total    = COALESCE((SELECT SUM(subtotal) FROM ventas.ticket_items WHERE ticket_id = t_id), 0) * (1 + t_rate)
    WHERE id = t_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ticket_items_totals ON ventas.ticket_items;
CREATE TRIGGER trg_ticket_items_totals
AFTER INSERT OR UPDATE OR DELETE ON ventas.ticket_items
FOR EACH ROW EXECUTE FUNCTION ventas.update_ticket_totals();

-- ============================================================
-- VISTAS COMPATIBLES
-- ============================================================

CREATE OR REPLACE VIEW ventas.v_ventas_hoy AS
SELECT COUNT(*) AS total_tickets,
       COALESCE(SUM(total), 0) AS total_vendido,
       COALESCE(AVG(total), 0) AS ticket_promedio
FROM ventas.tickets WHERE estado = 'pagado' AND pagado_en::date = CURRENT_DATE;

CREATE OR REPLACE VIEW ventas.v_top_productos AS
SELECT p.id, p.nombre, c.nombre AS categoria,
       SUM(ti.cantidad) AS unidades_vendidas,
       SUM(ti.subtotal) AS total_vendido
FROM ventas.ticket_items ti
JOIN ventas.tickets t   ON t.id = ti.ticket_id AND t.estado = 'pagado'
JOIN inventario.productos p ON p.id = ti.producto_id
JOIN inventario.categorias c ON c.id = p.categoria_id
GROUP BY p.id, p.nombre, c.nombre
ORDER BY unidades_vendidas DESC;

CREATE OR REPLACE VIEW ventas.v_comandas_estado AS
SELECT ci.estado, COUNT(*) AS cantidad
FROM ventas.comanda_items ci
JOIN ventas.comandas co ON co.id = ci.comanda_id
JOIN ventas.tickets  t  ON t.id  = co.ticket_id AND t.estado = 'abierto'
GROUP BY ci.estado;
