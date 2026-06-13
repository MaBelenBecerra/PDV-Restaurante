# Historial de Precios — Caso Individual
## Ventas + base de datos propia · Precio fijo por transacción

---

## ¿Qué verifica este caso?

El precio de venta debe quedar congelado en el momento de la transacción. Si el precio de un producto cambia después, el historial de ventas anteriores no debe cambiar. El dashboard mensual debe mostrar los valores correctos.

---

## El problema

```
Enero:  pizza a $10  →  50 ventas
Marzo:  precio sube a $15
Hoy:    dashboard muestra enero = 50 × $15 = $750  ❌
        debería mostrar         = 50 × $10 = $500  ✓
```

---

## Modelo correcto vs. incorrecto

```sql
-- ❌ Precio recalculado dinámicamente (incorrecto)
SELECT v.cantidad, p.precio, (v.cantidad * p.precio) AS subtotal
FROM ventas v JOIN productos p ON v.producto_id = p.id

-- ✅ Precio fijo en la transacción (correcto)
SELECT v.cantidad, v.precio_unitario, (v.cantidad * v.precio_unitario) AS subtotal
FROM ventas v
```

La diferencia está en el modelo de la tabla `ventas`: debe tener una columna `precio_unitario` que se guarda al momento de registrar la venta, no se lee del catálogo de productos.

---

## Verificación en vivo durante la defensa

1. Dashboard muestra métricas mes actual vs. mes anterior
2. Se cambia el precio de un producto
3. Pregunta: "¿cambió el número del mes pasado?"

La respuesta correcta es **no** — el historial queda intacto.