-- ============================================================
-- BASE DE DATOS: PDV-RESTAURANTE (POSTGRESQL MULTI-SCHEMA SCHEMA)
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
INSERT INTO public.empresas (cen, nombre, nit, activo) 
VALUES ('9f2a4e4e-ac9d-46a4-98ea-412d1c168d12', 'Restaurante El Sabor', '20123456789', 1) 
ON CONFLICT DO NOTHING;


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

-- Ajustes de Stock
CREATE TABLE IF NOT EXISTS inventario.ajustes_stock (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES inventario.productos(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('entrada','salida')),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    motivo TEXT NOT NULL,
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

CREATE OR REPLACE TRIGGER trg_ticket_items_totals
AFTER INSERT OR UPDATE OR DELETE ON ventas.ticket_items
FOR EACH ROW EXECUTE FUNCTION ventas.update_ticket_totals();


-- ============================================================
-- VISTAS COMPATIBLES DENTRO DEL ESQUEMA VENTAS
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


-- ============================================================
-- DATOS DE SEMILLA / PRUEBA
-- ============================================================

-- Estaciones KDS
INSERT INTO ventas.estaciones (id, nombre, tipo, cen, code) VALUES 
    (1, 'Cocina', 'cocina', 'cocina-cen-guid-1', 'EST-00001'),
    (2, 'Bar', 'bar', 'bar-cen-guid-2', 'EST-00002')
ON CONFLICT DO NOTHING;

-- Proveedores
INSERT INTO compras.proveedores (nombre, contacto, telefono, email, cen, code) VALUES
    ('Distribuidora ABC', 'Pedro López', '555-0001', 'pedrolopez@abc.com', 'sup-cen-1', 'SUP-00001'),
    ('Fresh Foods S.A.', 'María García', '555-0002', 'maria@freshfoods.com', 'sup-cen-2', 'SUP-00002'),
    ('Bebidas Premium', 'Carlos Rodríguez', '555-0003', 'carlos@bebidaspremium.com', 'sup-cen-3', 'SUP-00003')
ON CONFLICT DO NOTHING;

-- Categorías
INSERT INTO inventario.categorias (nombre, cen, code) VALUES 
    ('Entradas', 'cat-cen-1', 'CAT-00001'), 
    ('Platos principales', 'cat-cen-2', 'CAT-00002'), 
    ('Postres', 'cat-cen-3', 'CAT-00003'), 
    ('Bebidas', 'cat-cen-4', 'CAT-00004'), 
    ('Cócteles', 'cat-cen-5', 'CAT-00005') 
ON CONFLICT DO NOTHING;

-- Unidades
INSERT INTO inventario.unidades (nombre, cen, code) VALUES 
    ('Porción', 'uni-cen-1', 'UNI-00001'), 
    ('Unidad', 'uni-cen-2', 'UNI-00002'), 
    ('Vaso', 'uni-cen-3', 'UNI-00003'), 
    ('Botella', 'uni-cen-4', 'UNI-00004'), 
    ('Plato', 'uni-cen-5', 'UNI-00005') 
ON CONFLICT DO NOTHING;

-- Productos
INSERT INTO inventario.productos (categoria_id, unidad_id, nombre, precio, stock, cen, code, station_code) VALUES
    (1,1,'Ceviche mixto',45.00,20,'793108d6-626a-43f8-8344-be003ea264d2','PRO-00001','COCINA'),
    (1,1,'Tequeños',25.00,30,'834108d6-626a-43f8-8344-be003ea264d3','PRO-00002','COCINA'),
    (2,5,'Pollo a la brasa',55.00,15,'934108d6-626a-43f8-8344-be003ea264d4','PRO-00003','COCINA'),
    (2,5,'Lomo saltado',65.00,10,'a34108d6-626a-43f8-8344-be003ea264d5','PRO-00004','COCINA'),
    (3,2,'Suspiro limeño',20.00,12,'b34108d6-626a-43f8-8344-be003ea264d6','PRO-00005','COCINA'),
    (4,3,'Chicha morada',12.00,50,'c34108d6-626a-43f8-8344-be003ea264d7','PRO-00007','BAR'),
    (4,3,'Limonada',10.00,50,'d34108d6-626a-43f8-8344-be003ea264d8','PRO-00008','BAR'),
    (5,3,'Pisco sour',30.00,40,'e34108d6-626a-43f8-8344-be003ea264d9','PRO-00009','BAR')
ON CONFLICT DO NOTHING;

-- Corregir secuencias para SERIAL
SELECT setval('inventario.categorias_id_seq', COALESCE((SELECT MAX(id)+1 FROM inventario.categorias), 1), false);
SELECT setval('inventario.unidades_id_seq', COALESCE((SELECT MAX(id)+1 FROM inventario.unidades), 1), false);
SELECT setval('inventario.productos_id_seq', COALESCE((SELECT MAX(id)+1 FROM inventario.productos), 1), false);
SELECT setval('ventas.estaciones_id_seq', COALESCE((SELECT MAX(id)+1 FROM ventas.estaciones), 1), false);
SELECT setval('compras.proveedores_id_seq', COALESCE((SELECT MAX(id)+1 FROM compras.proveedores), 1), false);
