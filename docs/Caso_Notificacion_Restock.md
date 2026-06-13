# Notificación de Restock — Caso Individual
## Compras → Inventario → Ventas · Server-Sent Events (SSE)

---

## ¿Qué verifica este caso?

Cuando se registra una compra, el stock en Inventario sube automáticamente y Ventas recibe una notificación en tiempo real visible en pantalla. No se debe hacer polling — la notificación llega por SSE desde Inventario.

---

## ¿Por qué SSE y no WebSocket?

| | SSE | WebSocket |
|---|---|---|
| Dirección | Servidor → cliente | Bidireccional |
| Complejidad | Baja | Alta |
| Reconexión automática | ✓ Sí (nativa) | Manual |
| ¿Suficiente para este caso? | ✓ Sí | Overkill |

---

## Herramientas y paquetes

### Backend (.NET / ASP.NET Core)

| Herramienta | NuGet | Uso |
|---|---|---|
| ASP.NET Core (built-in) | ✗ No requiere | Streaming con `text/event-stream`, `Response.WriteAsync` |
| `System.Threading.Channels` | ✗ Incluido en .NET 5+ | Canal en memoria para pasar eventos entre el endpoint de compra y el endpoint SSE |
| `System.Text.Json` | ✗ Incluido en .NET 5+ | Serializar el evento antes de enviarlo |

El patrón central es registrar un `Channel<T>` como **Singleton** en el contenedor de DI. El endpoint de compra escribe al canal; el endpoint SSE lee del canal y transmite.

```csharp
// Program.cs — registrar el canal como singleton
builder.Services.AddSingleton(Channel.CreateUnbounded<RestockEvent>());
```

### Frontend (React)

| Herramienta | npm | Uso |
|---|---|---|
| `EventSource` (built-in browser) | ✗ No requiere | Conectar al endpoint SSE y recibir eventos |
| `@microsoft/fetch-event-source` | ✓ Opcional | Si se necesita enviar headers (ej. Authorization) o control de reconexión manual |

---

## Implementación mínima esperada

### Endpoint SSE en Inventario

```csharp
[HttpGet("restock-events")]
public async Task StreamRestockEvents(CancellationToken ct)
{
    Response.Headers["Content-Type"] = "text/event-stream";
    Response.Headers["Cache-Control"] = "no-cache";

    await foreach (var evento in _restockChannel.ReadAllAsync(ct))
    {
        await Response.WriteAsync($"data: {JsonSerializer.Serialize(evento)}\n\n");
        await Response.Body.FlushAsync(ct);
    }
}
```

### Consumidor en Ventas (frontend React)

```javascript
const source = new EventSource(`${INVENTORY_URL}/restock-events`);
source.onmessage = (e) => {
    const restock = JSON.parse(e.data);
    toast.info(`Restock: ${restock.producto} +${restock.cantidad} unidades`);
};
```