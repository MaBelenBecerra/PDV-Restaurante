# Restaurante PDV (Arquitectura Distribuida con PostgreSQL)

Sistema completo de Punto de Venta (PDV) para restaurantes con frontend interactivo en React + Vite y un backend distribuido compuesto por 3 microservicios independientes que se comunican mediante HTTP y comparten una base de datos local unificada en PostgreSQL.

---

## 🏗️ Arquitectura del Sistema

El backend ha sido modularizado y desacoplado en tres APIs totalmente independientes situadas al mismo nivel del frontend:

1. **Inventory.Api (Puerto `5143`)**: Controla el catálogo de productos, categorías, unidades y el stock de inventario.
2. **Sales.Api (Puerto `5074`)**: Gestiona la creación de tickets, adición de ítems con validación de stock, facturación/pagos, KDS (Kitchen Display System para cocina y bar) y reportes de dashboard.
3. **Purchases.Api (Puerto `5229`)**: Administra la gestión de proveedores e histórico de órdenes de compra para reabastecimiento de mercadería.

---

## 🛠️ Requisitos Previos

Asegúrate de contar con lo siguiente instalado en tu equipo local:
- **Python 3.9+**
- **Node.js 18+**
- **PostgreSQL 14+** y **pgAdmin 4** (u otra herramienta de base de datos)

---

## 🚀 Guía de Instalación y Configuración Paso a Paso

### Paso 1: Configurar la Base de Datos en PostgreSQL y pgAdmin

1. **Abrir pgAdmin**: Conéctate a tu servidor local de PostgreSQL.
2. **Crear la Base de Datos**:
   - Haz clic derecho sobre **Databases** -> **Create** -> **Database...**
   - Asigna el nombre **`pdv_restaurante`** y presiona **Save**.
3. **Ejecutar el Script SQL**:
   - Selecciona la base de datos `pdv_restaurante` recién creada.
   - Ve a la barra de herramientas superior y selecciona **Tools** -> **Query Tool** (Consola de consultas).
   - Abre el archivo [database/postgres_schema.sql](database/postgres_schema.sql), copia su contenido completo y pégalo en la consola de pgAdmin.
   - Presiona el botón de ejecutar **Execute/Refresh** (icono de play) o presiona **F5**. Esto creará la estructura completa de esquemas (`inventario`, `ventas`, `compras`), tablas, disparadores automáticos de totales en PL/pgSQL, vistas compatibles y cargará los productos y estaciones iniciales de prueba.

---

### Paso 2: Instalar Dependencias y Configurar Entornos

Puedes iniciar y configurar todo de forma automática mediante scripts, o realizar el proceso de instalación y arranque paso a paso de manera manual.

#### Opción A: Configuración y Arranque Automático (Recomendado)

El proyecto cuenta con scripts que configuran las variables de entorno por defecto, instalan las dependencias de Python y Node.js y encienden todos los servidores.

- **En Windows**: 
  Haz doble clic en el archivo `start.bat` o ejecútalo desde PowerShell/CMD en la raíz del proyecto:
  ```bash
  .\start.bat
  ```
- **En Linux / macOS**:
  Otorga permisos de ejecución y ejecuta el script:
  ```bash
  chmod +x start.sh
  ./start.sh
  ```

#### Opción B: Instalación y Configuración Manual

Si prefieres realizar el proceso de instalación y arranque de forma manual, sigue estos pasos:

1. **Configurar archivos de entorno (`.env`)**:
   En cada una de las carpetas de backend (`Inventory.Api`, `Sales.Api` y `Purchases.Api`):
   - Copia el archivo `.env.example` y renómbralo a `.env`.
   - Edita el archivo `.env` configurando los accesos a tu PostgreSQL local:
     ```ini
     DB_HOST=localhost
     DB_PORT=5432
     DB_NAME=pdv_restaurante
     DB_USER=tu_usuario_postgres
     DB_PASSWORD=tu_contraseña_postgres
     ```

2. **Instalar dependencias y ejecutar las APIs (Backend)**:
   - Abre tres terminales separadas (una para cada API).
   - Crea y activa un entorno virtual en cada carpeta o de forma global (opcional).
   - Instala las dependencias en cada directorio y ejecuta el backend correspondiente:
     
     * **Inventory API**:
       ```bash
       cd Inventory.Api
       pip install -r requirements.txt
       python app.py
       ```
     * **Sales API**:
       ```bash
       cd Sales.Api
       pip install -r requirements.txt
       python app.py
       ```
     * **Purchases API**:
       ```bash
       cd Purchases.Api
       pip install -r requirements.txt
       python app.py
       ```

3. **Instalar dependencias y ejecutar la Interfaz (Frontend)**:
   - Abre una cuarta terminal en la carpeta raíz del proyecto y dirígete a `frontend`:
     ```bash
     cd frontend
     npm install
     npm run dev
     ```

---

## 🌐 Puertos del Ecosistema y Documentación (Swagger UI)

Una vez que los servicios estén activos, podrás acceder a ellos y explorar su API interactiva a través de los siguientes enlaces locales:

- **Frontend (Vite + React)**: [http://localhost:5173](http://localhost:5173)
- **Inventory API (Microservicio)**: [http://localhost:5143](http://localhost:5143) | 📖 Swagger UI: [http://localhost:5143/swagger](http://localhost:5143/swagger)
- **Sales API (Microservicio)**: [http://localhost:5074](http://localhost:5074) | 📖 Swagger UI: [http://localhost:5074/swagger](http://localhost:5074/swagger)
- **Purchases API (Microservicio)**: [http://localhost:5229](http://localhost:5229)

---

## 💻 Guía de Uso del Sistema (Flujo Completo)

Una vez que tengas la aplicación abierta en tu navegador ([http://localhost:5173](http://localhost:5173)), sigue este flujo para probar todas sus funcionalidades integradas:

### 1. Gestión de Cuentas en el PDV
1. Navega a la sección **🧾 PDV** en la barra de navegación izquierda.
2. En la barra lateral izquierda del PDV, presiona el botón **+ Nueva Cuenta**.
3. Se abrirá un modal pidiendo el **Nombre del Mesero**. Introduce un nombre (ej: `Carlos`) y presiona **Crear Cuenta**.
4. La cuenta recién creada aparecerá en el panel de **Cuentas Abiertas** con un total inicial de `Bs. 0.00` y su respectivo identificador abreviado. Haz clic sobre la cuenta para seleccionarla.

### 2. Adición de Items con Descuento de Stock en Tiempo Real
1. Al seleccionar la cuenta, se activará el panel central con el **Catálogo de Productos** y el panel derecho con el **Detalle del Ticket**.
2. Filtra los productos haciendo clic en las píldoras de **Categorías** (Bebidas, Entradas, Platos principales, Postres) o utiliza el cuadro de **Búsqueda** superior.
3. Haz clic en un producto (ej: *Lomo saltado*). Verás que se agrega instantáneamente en el panel del ticket derecho con una cantidad inicial de `1`.
4. **Prueba de No Duplicidad**: Haz clic nuevamente en el mismo producto. En lugar de aparecer como un item repetido en el ticket, su cantidad se incrementará automáticamente a `2` y se actualizarán los totales del ticket.
5. Modifica cantidades directamente usando los botones **`+`** o **`−`** del item, o agrega notas de cocina especiales (ej. *"Término medio"* o *"Sin cebolla"*).

### 3. Envío de Comanda a Cocina o Bar (KDS)
1. Con los productos añadidos a la comanda, presiona el botón **📤 Enviar Comanda** en el panel derecho.
2. El sistema enviará una notificación y registrará el estado de preparación de los ítems.
3. Dirígete a la sección **👨‍🍳 Cocina** o **🍸 Bar** desde el menú principal de navegación de la izquierda.
4. Verás en tiempo real las tarjetas de comanda con el estado **PENDIENTE**, detallando los ítems de comida o bebida, cantidades y las notas especiales ingresadas en el PDV.
5. Cuando el pedido esté preparado en cocina o bar, presiona el botón correspondiente de la tarjeta para marcarlo como listo. Su estado pasará a actualizarse dinámicamente en el sistema.

### 4. Cobro y Cierre de la Cuenta
1. Vuelve a la sección **🧾 PDV** y selecciona la cuenta activa de tu mesa.
2. Presiona el botón **💳 Cobrar**.
3. Se abrirá el modal de **Procesar Pago** mostrando el monto total neto (incluyendo el cálculo automático del 13% de impuesto de ley).
4. Elige un método de pago (*💵 Efectivo*, *📱 Código QR*, *💳 Tarjeta*) y presiona **Confirmar Pago**.
5. La cuenta se cerrará formalmente, su estado pasará a `PAGADO` en PostgreSQL y desaparecerá de la lista de cuentas abiertas del PDV.
6. *Nota de Integración*: Al completarse el pago, la API de Ventas se comunica de manera interna con la API de Inventario por medio de HTTP para descontar de forma definitiva del stock de la base de datos las cantidades exactas de productos vendidos.

### 5. Análisis en el Dashboard
1. Navega a la sección **🏠 Dashboard** en el menú izquierdo.
2. Visualizarás los ingresos diarios, gráficos comparativos de ventas de los productos más populares y los tiempos/estados de las comandas de cocina y bar.
3. Todos estos datos se calculan directamente en la base de datos gracias a las vistas `v_ventas_hoy` y `v_top_productos` en PostgreSQL.

---

## 🧪 Pruebas de Integración y Verificación

Para certificar la comunicación de red entre microservicios e integridad referencial de base de datos sin levantar la UI:
1. Inicia las APIs y el frontend (`start.bat` o `start.sh`).
2. Abre una terminal nueva en la raíz del proyecto y ejecuta:
   ```bash
   python database/verify_distributed.py
   ```
3. El script simulará programáticamente todo el flujo de ventas, comprobando health checks, agregando ítems, cobrando el ticket y verificando que el stock de inventario se descuente de forma exacta.

---

## ⚙️ Estructura de Directorios

```
PDV-Restaurante/
├── Inventory.Api/              # Microservicio de Inventario y Catálogo (Puerto 5143)
│   ├── app.py                  # Servidor de Flask
│   ├── database.py             # Capa de datos PostgreSQL
│   ├── requirements.txt        # Dependencias de Python
│   └── routes/                 # Controladores/Rutas del catálogo y stock
├── Sales.Api/                  # Microservicio de Ventas, KDS y Facturación (Puerto 5074)
│   ├── app.py                  # Servidor de Flask
│   ├── database.py             # Capa de datos PostgreSQL
│   ├── requirements.txt        # Dependencias de Python
│   ├── inventory_client.py     # Cliente HTTP para comunicación cross-service con Inventario
│   └── routes/                 # Controladores/Rutas de tickets, pagos y comandas
├── Purchases.Api/              # Microservicio de Compras y Proveedores (Puerto 5229)
│   ├── app.py                  # Servidor de Flask
│   ├── database.py             # Capa de datos PostgreSQL
│   ├── requirements.txt        # Dependencias de Python
│   ├── inventory_client.py     # Cliente HTTP para actualización de inventario
│   └── routes/                 # Controladores/Rutas de compras y proveedores
├── database/                   # Recursos de base de datos y scripts de verificación
│   ├── postgres_schema.sql     # Script SQL para creación de esquema y semillas en pgAdmin
│   └── verify_distributed.py   # Script de verificación de flujos distribuidos
├── frontend/                   # Interfaz de Usuario en React + Vite (Puerto 5173)
├── start.bat                   # Ejecutor automático para entornos Windows
└── start.sh                    # Ejecutor automático para entornos Unix-based
```

---

## 📝 Licencia

Este proyecto está bajo la licencia MIT.

