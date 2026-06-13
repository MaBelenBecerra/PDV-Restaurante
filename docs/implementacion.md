# Guía de Implementación — Integración Final (Examen)

Este documento describe la hoja de ruta técnica para implementar los 3 casos de integración solicitados en los backends de **Inventario**, **Ventas** y **Compras**. Se asume que los backends ya operan con sus entidades base y respetan el uso de identificadores CEN para comunicación entre servicios.

---

## 1. Endpoints Nuevos y de Integración

A continuación se listan los endpoints que deben ser creados o modificados específicamente para cumplir con los casos de examen (omitiendo la gestión básica de CRUDs pre-existentes u otros endpoints en particular de su propio sistema si existiera).

### Inventario (Inventory.API)
| Endpoint | Verbo | Propósito | Valor en la Integración |
| :--- | :--- | :--- | :--- |
| `/api/inventory/companies/{companyCen}/restock-events` | `GET` | **SSE (Server-Sent Events)** | Permite que otros servicios (Ventas) escuchen en tiempo real cuando llega mercadería. |

### Ventas (Sales.API)
| Endpoint | Verbo | Propósito | Valor en la Integración |
| :--- | :--- | :--- | :--- |
| `/api/sales/companies/{companyCen}/dashboard/monthly` | `GET` | **Dashboard Comparativo** | Demuestra la veracidad del historial de precios (Mes Actual vs Mes Anterior). |

### Compras (Purchase.API)
| Endpoint | Verbo | Cambio en Lógica | Valor en la Integración |
| :--- | :--- | :--- | :--- |
| `/api/purchases/companies/{companyCen}/orders/{orderCen}/receive` | `POST` | **Trigger de Stock** | Al recibir, debe llamar a la API de Inventario (`/stock/increase`). Es el origen de la cadena de integración. |

---

## 2. Caso A: Notificación de Restock (SSE)
**Flujo:** Compras → Inventario → Ventas

### Estrategia de Implementación Genérica
1.  **Inventario (Backend):**
    *   Registrar un `Channel<RestockEvent>` como **Singleton** en `Program.cs`.
    *   El endpoint `/restock-events` debe leer del canal usando un `await foreach` y escribir a la respuesta con `text/event-stream`.
    *   **Importante:** Cada vez que el endpoint `/stock/increase` procese un ingreso, debe escribir un objeto en este Canal.
2.  **Ventas (Frontend/Client):**
    *   Implementar un Hook o componente que inicialice un `new EventSource(URL_INVENTARIO)`.
    *   Debe mostrar una notificación (Toast/Alerta) cuando reciba el evento JSON.

---

## 3. Caso B: Resiliencia con Polly
**Flujo:** Ventas → Inventario (Simulación de caída)

### Estrategia de Implementación Genérica
Este caso no es un endpoint, sino una **capa de protección** en los clientes HTTP de Ventas (o cualquier servicio que llame a otro).
1.  **Políticas mínimas:**
    *   **Retry:** Reintentar 3 veces con una espera exponencial (2, 4, 8 segundos).
    *   **Circuit Breaker:** Si fallan 5 llamadas seguidas, "abrir el circuito" por 30 segundos para no saturar al servicio caído.
    *   **Fallback:** Si la llamada falla definitivamente, retornar un objeto con valores por defecto o un mensaje controlado en lugar de lanzar una excepción 500.
2.  **Configuración:** Debe aplicarse al configurar el `HttpClient` en la capa de **Infraestructura**.

---

## 4. Caso C: Historial de Precios (Inmutabilidad)
**Flujo:** Registro de Venta → Dashboard Mensual

### Requisitos del Modelo de Base de Datos
Para que el historial sea "veraz", el sistema no debe depender del precio actual del producto al consultar ventas pasadas.
*   **Entidad TicketItem / DetalleVenta:** **DEBE** tener una columna `UnitPrice` (decimal/numeric).
*   **Acción al vender:** El servicio de Ventas debe consultar el catálogo de Inventario (o su caché), obtener el precio del momento y **guardarlo físicamente** en la fila del detalle del ticket.

### Lógica del Dashboard
El query del dashboard debe ser simple:
*   `Total = SUM(Cantidad * UnitPrice)` directamente de la tabla de ventas/detalles.
*   **Prueba de fuego:** Si cambias el precio de un producto en Inventario hoy, el total de las ventas de ayer en el dashboard **no debe cambiar**.

---

## 5. Flujo de Datos Esperado (Cadena de Integración)

1.  **Compras:** Se ejecuta `.../orders/{orderCen}/receive`.
2.  **Integración 1:** Compras envía un `POST` a Inventario (`/stock/increase`).
3.  **Inventario:** Actualiza tablas de Stock y Kardex.
4.  **Evento:** Inventario publica el cambio en el `Channel<T>` interno.
5.  **Notificación:** El endpoint SSE de Inventario envía el evento a **Ventas (Frontend)**.
6.  **Visualización:** El usuario de Ventas ve: *"Stock aumentado para [ProductoCEN] + [Cantidad]"*.

---

## 6. Reglas de Oro para el Grupo
*   **Identificadores:** Usar siempre el `ProductCen`, `CompanyCen`, etc., en las peticiones entre servicios. Nunca usar IDs autoincrementales internos de la DB de otro módulo.
*   **Contratos:** Los DTOs deben mapearse exactamente a los nombres de campos del `contrato-api.yaml` (ej. si el contrato dice `unitPrice`, el JSON no puede enviar `precioUnitario`).
*   **Aislamiento:** Si el backend de Inventario no está disponible, el backend de Ventas debe seguir funcionando (aunque sea con datos limitados) gracias a Polly.
