PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Configuración global (1 sola fila, id siempre = 1)
CREATE TABLE IF NOT EXISTS configuracion (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    tasa_impuesto  REAL    NOT NULL DEFAULT 0.13,
    actualizado_en TEXT    NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO configuracion (id, tasa_impuesto) VALUES (1, 0.13);

CREATE TABLE IF NOT EXISTS categorias (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS unidades (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS productos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    unidad_id    INTEGER NOT NULL REFERENCES unidades(id),
    nombre       TEXT    NOT NULL,
    precio       REAL    NOT NULL CHECK (precio > 0),
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    activo       INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    agotado      INTEGER NOT NULL DEFAULT 0 CHECK (agotado IN (0,1)),
    creado_en    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ajustes_stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo        TEXT    NOT NULL CHECK (tipo IN ('entrada','salida')),
    cantidad    INTEGER NOT NULL CHECK (cantidad > 0),
    motivo      TEXT    NOT NULL,
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clientes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL,
    telefono  TEXT,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id    INTEGER REFERENCES clientes(id),
    mesero        TEXT NOT NULL,
    estado        TEXT NOT NULL DEFAULT 'abierto'
                       CHECK (estado IN ('abierto','pagado','cancelado')),
    subtotal      REAL NOT NULL DEFAULT 0,
    impuesto      REAL NOT NULL DEFAULT 0,
    total         REAL NOT NULL DEFAULT 0,
    tasa_impuesto REAL NOT NULL DEFAULT 0.13,
    creado_en     TEXT NOT NULL DEFAULT (datetime('now')),
    pagado_en     TEXT
);

CREATE TABLE IF NOT EXISTS ticket_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id       INTEGER NOT NULL REFERENCES tickets(id),
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL    NOT NULL CHECK (precio_unitario > 0),
    subtotal        REAL    NOT NULL,
    nota            TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS pagos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL UNIQUE REFERENCES tickets(id),
    metodo    TEXT    NOT NULL CHECK (metodo IN ('efectivo','qr','tarjeta')),
    monto     REAL    NOT NULL CHECK (monto > 0),
    creado_en TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS estaciones (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    tipo   TEXT NOT NULL CHECK (tipo IN ('cocina','bar'))
);
INSERT OR IGNORE INTO estaciones (id, nombre, tipo) VALUES (1,'Cocina','cocina');
INSERT OR IGNORE INTO estaciones (id, nombre, tipo) VALUES (2,'Bar','bar');

CREATE TABLE IF NOT EXISTS comandas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL REFERENCES tickets(id),
    estacion_id INTEGER NOT NULL REFERENCES estaciones(id),
    es_reenvio  INTEGER NOT NULL DEFAULT 0 CHECK (es_reenvio IN (0,1)),
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS comanda_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id     INTEGER NOT NULL REFERENCES comandas(id),
    ticket_item_id INTEGER NOT NULL REFERENCES ticket_items(id),
    estado         TEXT    NOT NULL DEFAULT 'pendiente'
                           CHECK (estado IN ('pendiente','en_preparacion','listo')),
    actualizado_en TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Triggers: recalcular totales automáticamente
CREATE TRIGGER IF NOT EXISTS trg_totales_insert AFTER INSERT ON ticket_items BEGIN
    UPDATE tickets SET
        subtotal = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = NEW.ticket_id),
        impuesto = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = NEW.ticket_id) * tasa_impuesto,
        total    = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = NEW.ticket_id) * (1 + tasa_impuesto)
    WHERE id = NEW.ticket_id;
END;
CREATE TRIGGER IF NOT EXISTS trg_totales_update AFTER UPDATE ON ticket_items BEGIN
    UPDATE tickets SET
        subtotal = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = NEW.ticket_id),
        impuesto = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = NEW.ticket_id) * tasa_impuesto,
        total    = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = NEW.ticket_id) * (1 + tasa_impuesto)
    WHERE id = NEW.ticket_id;
END;
CREATE TRIGGER IF NOT EXISTS trg_totales_delete AFTER DELETE ON ticket_items BEGIN
    UPDATE tickets SET
        subtotal = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = OLD.ticket_id),
        impuesto = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = OLD.ticket_id) * tasa_impuesto,
        total    = (SELECT COALESCE(SUM(subtotal),0) FROM ticket_items WHERE ticket_id = OLD.ticket_id) * (1 + tasa_impuesto)
    WHERE id = OLD.ticket_id;
END;
CREATE TRIGGER IF NOT EXISTS trg_descontar_stock AFTER INSERT ON pagos BEGIN
    UPDATE productos SET stock = stock - (
        SELECT SUM(cantidad) FROM ticket_items
        WHERE ticket_id = NEW.ticket_id AND producto_id = productos.id
    )
    WHERE id IN (SELECT DISTINCT producto_id FROM ticket_items WHERE ticket_id = NEW.ticket_id);
    UPDATE tickets SET estado = 'pagado', pagado_en = datetime('now') WHERE id = NEW.ticket_id;
END;

-- Vistas para el dashboard
CREATE VIEW IF NOT EXISTS v_ventas_hoy AS
SELECT COUNT(*) AS total_tickets,
       COALESCE(SUM(total),0) AS total_vendido,
       COALESCE(AVG(total),0) AS ticket_promedio
FROM tickets WHERE estado = 'pagado' AND date(pagado_en) = date('now');

CREATE VIEW IF NOT EXISTS v_top_productos AS
SELECT p.id, p.nombre, c.nombre AS categoria,
       SUM(ti.cantidad) AS unidades_vendidas,
       SUM(ti.subtotal) AS total_vendido
FROM ticket_items ti
JOIN tickets t   ON t.id = ti.ticket_id AND t.estado = 'pagado'
JOIN productos p ON p.id = ti.producto_id
JOIN categorias c ON c.id = p.categoria_id
GROUP BY p.id ORDER BY unidades_vendidas DESC;

CREATE VIEW IF NOT EXISTS v_comandas_estado AS
SELECT ci.estado, COUNT(*) AS cantidad
FROM comanda_items ci
JOIN comandas co ON co.id = ci.comanda_id
JOIN tickets  t  ON t.id  = co.ticket_id AND t.estado = 'abierto'
GROUP BY ci.estado;

-- Módulo de Compras
CREATE TABLE IF NOT EXISTS proveedores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    contacto  TEXT,
    telefono  TEXT,
    email     TEXT,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS compras (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    estado      TEXT NOT NULL DEFAULT 'pendiente'
                     CHECK (estado IN ('pendiente','confirmada','cancelada')),
    fecha       TEXT NOT NULL DEFAULT (datetime('now')),
    total       REAL NOT NULL DEFAULT 0,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now')),
    confirmado_en TEXT
);

CREATE TABLE IF NOT EXISTS compra_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    compra_id   INTEGER NOT NULL REFERENCES compras(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad    INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL CHECK (precio_unitario > 0),
    subtotal    REAL NOT NULL
);

-- Trigger: aumentar stock cuando se confirma compra
CREATE TRIGGER IF NOT EXISTS trg_aumentar_stock AFTER UPDATE ON compras
WHEN NEW.estado = 'confirmada' AND OLD.estado != 'confirmada'
BEGIN
    UPDATE productos SET stock = stock + (
        SELECT COALESCE(SUM(cantidad),0) FROM compra_items
        WHERE compra_id = NEW.id AND producto_id = productos.id
    )
    WHERE id IN (SELECT DISTINCT producto_id FROM compra_items WHERE compra_id = NEW.id);
    
    INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo)
    SELECT producto_id, 'entrada', cantidad, 'Compra confirmada #' || NEW.id
    FROM compra_items WHERE compra_id = NEW.id;
    
    UPDATE compras SET confirmado_en = datetime('now') WHERE id = NEW.id;
END;

-- Vista: compras pendientes
CREATE VIEW IF NOT EXISTS v_compras_pendientes AS
SELECT c.id, c.proveedor_id, p.nombre AS proveedor, c.estado,
       COUNT(ci.id) AS total_items,
       COALESCE(SUM(ci.subtotal),0) AS total,
       c.fecha
FROM compras c
JOIN proveedores p ON p.id = c.proveedor_id
LEFT JOIN compra_items ci ON ci.compra_id = c.id
WHERE c.estado = 'pendiente'
GROUP BY c.id;

-- Datos de prueba: proveedores
INSERT OR IGNORE INTO proveedores (nombre, contacto, telefono, email) VALUES
    ('Distribuidora ABC', 'Pedro López', '555-0001', 'pedrolópez@distribuiodora.com'),
    ('Fresh Foods S.A.', 'María García', '555-0002', 'maria@freshfoods.com'),
    ('Bebidas Premium', 'Carlos Rodríguez', '555-0003', 'carlos@bebidaspremium.com');

-- Datos de prueba iniciales
INSERT OR IGNORE INTO categorias (nombre) VALUES
    ('Entradas'),('Platos principales'),('Postres'),('Bebidas'),('Cócteles');
INSERT OR IGNORE INTO unidades (nombre) VALUES
    ('Porción'),('Unidad'),('Vaso'),('Botella'),('Plato');
INSERT OR IGNORE INTO productos (categoria_id, unidad_id, nombre, precio, stock) VALUES
    (1,1,'Ceviche mixto',45.00,20),(1,1,'Tequeños',25.00,30),
    (2,5,'Pollo a la brasa',55.00,15),(2,5,'Lomo saltado',65.00,10),
    (3,2,'Suspiro limeño',20.00,12),(4,3,'Chicha morada',12.00,50),
    (4,3,'Limonada',10.00,50),(5,3,'Pisco sour',30.00,40);
