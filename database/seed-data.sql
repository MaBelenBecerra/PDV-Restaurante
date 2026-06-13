-- ============================================================
-- BASE DE DATOS: PDV-RESTAURANTE (POSTGRESQL SEED DATA)
-- ============================================================

BEGIN;

-- 1. Empresas
INSERT INTO public.empresas (cen, nombre, nit, activo) 
VALUES ('9f2a4e4e-ac9d-46a4-98ea-412d1c168d12', 'Restaurante El Sabor', '20123456789', 1) 
ON CONFLICT DO NOTHING;

-- 2. Estaciones KDS
INSERT INTO ventas.estaciones (id, nombre, tipo, cen, code) VALUES 
    (1, 'Cocina', 'cocina', 'cocina-cen-guid-1', 'EST-00001'),
    (2, 'Bar', 'bar', 'bar-cen-guid-2', 'EST-00002')
ON CONFLICT DO NOTHING;

-- 3. Proveedores
INSERT INTO compras.proveedores (nombre, contacto, telefono, email, cen, code) VALUES
    ('Distribuidora ABC', 'Pedro López', '555-0001', 'pedrolopez@abc.com', 'sup-cen-1', 'SUP-00001'),
    ('Fresh Foods S.A.', 'María García', '555-0002', 'maria@freshfoods.com', 'sup-cen-2', 'SUP-00002'),
    ('Bebidas Premium', 'Carlos Rodríguez', '555-0003', 'carlos@bebidaspremium.com', 'sup-cen-3', 'SUP-00003')
ON CONFLICT (nombre) DO NOTHING;

-- 4. Categorías
INSERT INTO inventario.categorias (nombre, cen, code) VALUES 
    ('Entradas', 'cat-cen-1', 'CAT-00001'), 
    ('Platos principales', 'cat-cen-2', 'CAT-00002'), 
    ('Postres', 'cat-cen-3', 'CAT-00003'), 
    ('Bebidas', 'cat-cen-4', 'CAT-00004'), 
    ('Cócteles', 'cat-cen-5', 'CAT-00005') 
ON CONFLICT (nombre) DO NOTHING;

-- 5. Unidades de Medida
INSERT INTO inventario.unidades (nombre, cen, code) VALUES 
    ('Porción', 'uni-cen-1', 'UNI-00001'), 
    ('Unidad', 'uni-cen-2', 'UNI-00002'), 
    ('Vaso', 'uni-cen-3', 'UNI-00003'), 
    ('Botella', 'uni-cen-4', 'UNI-00004'), 
    ('Plato', 'uni-cen-5', 'UNI-00005') 
ON CONFLICT (nombre) DO NOTHING;

-- 6. Meseros
INSERT INTO ventas.meseros (nombre, cen, email, telefono, activo) VALUES
    ('Juan Pérez', 'waiter-cen-guid-1', 'juan.perez@restaurante.local', '555-0199', 1),
    ('María López', 'waiter-cen-guid-2', 'maria.lopez@restaurante.local', '555-0188', 1)
ON CONFLICT (cen) DO NOTHING;

-- 7. Productos
INSERT INTO inventario.productos (categoria_id, unidad_id, nombre, precio, stock, cen, code, station_code) VALUES
    (1,1,'Ceviche mixto',45.00,20,'793108d6-626a-43f8-8344-be003ea264d2','PRO-00001','COCINA'),
    (1,1,'Tequeños',25.00,30,'834108d6-626a-43f8-8344-be003ea264d3','PRO-00002','COCINA'),
    (2,5,'Pollo a la brasa',55.00,15,'934108d6-626a-43f8-8344-be003ea264d4','PRO-00003','COCINA'),
    (2,5,'Lomo saltado',65.00,10,'a34108d6-626a-43f8-8344-be003ea264d5','PRO-00004','COCINA'),
    (3,2,'Suspiro limeño',20.00,12,'b34108d6-626a-43f8-8344-be003ea264d6','PRO-00005','COCINA'),
    (4,3,'Chicha morada',12.00,50,'c34108d6-626a-43f8-8344-be003ea264d7','PRO-00007','BAR'),
    (4,3,'Limonada',10.00,50,'d34108d6-626a-43f8-8344-be003ea264d8','PRO-00008','BAR'),
    (5,3,'Pisco sour',30.00,40,'e34108d6-626a-43f8-8344-be003ea264d9','PRO-00009','BAR')
ON CONFLICT (code) DO NOTHING;

-- 8. Bodega por Defecto
INSERT INTO inventario.bodegas (cen, nombre, activo)
VALUES ('alm-cen-guid-1', 'Almacén principal', 1)
ON CONFLICT (cen) DO NOTHING;

-- Corregir secuencias para campos SERIAL
SELECT setval('inventario.categorias_id_seq', COALESCE((SELECT MAX(id)+1 FROM inventario.categorias), 1), false);
SELECT setval('inventario.unidades_id_seq', COALESCE((SELECT MAX(id)+1 FROM inventario.unidades), 1), false);
SELECT setval('inventario.productos_id_seq', COALESCE((SELECT MAX(id)+1 FROM inventario.productos), 1), false);
SELECT setval('ventas.estaciones_id_seq', COALESCE((SELECT MAX(id)+1 FROM ventas.estaciones), 1), false);
SELECT setval('compras.proveedores_id_seq', COALESCE((SELECT MAX(id)+1 FROM compras.proveedores), 1), false);
SELECT setval('ventas.meseros_id_seq', COALESCE((SELECT MAX(id)+1 FROM ventas.meseros), 1), false);

COMMIT;
