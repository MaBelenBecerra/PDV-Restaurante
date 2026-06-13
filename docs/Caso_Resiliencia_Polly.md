# Resiliencia con Polly — Caso Individual
## Ventas → Inventario (caído simulado) · Polly

---

## ¿Qué verifica este caso?

Cuando Inventario no responde, Ventas debe responder de forma controlada sin crashear. El sistema no puede fallar silenciosamente — debe retornar un mensaje claro al cliente.

---

## Cómo simular la caída sin tocar AWS

```bash
# Cambiar en .env de Ventas y reiniciar (~10 segundos)
INVENTORY_URL=http://url-invalida-simulada:9999
```

Para restaurar: revertir la URL original y reiniciar.

---

## Políticas Polly esperadas (al menos una implementada)

### Retry

```csharp
var retryPolicy = Policy
    .Handle<HttpRequestException>()
    .WaitAndRetryAsync(
        retryCount: 3,
        sleepDurationProvider: attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt))
    );
```

### Circuit Breaker

```csharp
var circuitBreaker = Policy
    .Handle<HttpRequestException>()
    .CircuitBreakerAsync(
        exceptionsAllowedBeforeBreaking: 5,
        durationOfBreak: TimeSpan.FromSeconds(30)
    );
```

### Fallback

```csharp
var fallback = Policy<StockResponse>
    .Handle<HttpRequestException>()
    .FallbackAsync(new StockResponse {
        Disponible = false,
        Mensaje = "Inventario no disponible temporalmente"
    });
```

### Combinadas (ideal)

```csharp
var resiliencePolicy = Policy.WrapAsync(fallback, retryPolicy, circuitBreaker);
```