# Inventory Service

Microservicio demostrativo del bounded context Inventario: Python, FastAPI y SQLite.
Es independiente de Orders y no se comunica con él. No requiere MySQL.

## Ejecutar

Desde esta carpeta, con Python 3.10 o superior (verificado con Python 3.14.7):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

SQLite se crea automáticamente en `data/inventory.db`. Opcionalmente configura
`INVENTORY_DB_PATH` con otra ruta antes de iniciar. Conserva ese archivo entre
reinicios para conservar los productos. No necesitas crear tablas manualmente.
Documentación interactiva de FastAPI: http://127.0.0.1:8000/docs.

## Endpoints y demo

```bash
# Crear: 201. SQLite genera el ID.
curl -i -X POST http://127.0.0.1:8000/productos \
  -H 'Content-Type: application/json' \
  -d '{"nombre":"Teclado","precio":4.50,"stockDisponible":10}'

# Consultar: 200, stock 10
curl -i http://127.0.0.1:8000/productos/1

# Reservar: 200, stock 8
curl -i -X POST http://127.0.0.1:8000/productos/1/reservar \
  -H 'Content-Type: application/json' -d '{"cantidad":2}'
```

Producto inexistente: 404. Stock insuficiente: 409.
Datos inválidos de dominio: 400. JSON o tipos inválidos: 422.
El stock y la cantidad deben ser enteros. El precio debe ser un número JSON positivo
finito, con hasta dos decimales (máximo 9999999999.99), nunca una cadena.
Los identificadores y el stock persistido tienen el límite técnico de los enteros
SQLite de 64 bits; se valida en la entrada HTTP.

## Pruebas

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m pip check
```

Las pruebas verifican creación, ID/nombre válidos, stock no negativo,
reserva válida, stock insuficiente, cantidades no positivas y listado HTTP.
También se verificaron los tres endpoints con un servidor real y una base temporal:
crear con stock 10, reservar 2, comprobar SQLite y reiniciar conservando stock 8.
La verificación no deja productos de prueba en la base de desarrollo.

## DDD y SOLID para la sustentación

- **Bounded Context:** Inventario tiene modelo y base propios.
- **Aggregate Root:** `ProductoStock` es la entrada a las reglas de su stock;
  `reservar()` controla los cambios. Sus campos no admiten asignación directa normal.
- **Invariantes:** ID positivo tras persistir (None antes de crear), precio Decimal positivo
  finito con hasta dos decimales, nombre no vacío, stock entero no negativo,
  cantidad de reserva positiva y no superior al disponible.
- **Lenguaje ubicuo:** `ProductoStock`, `consultar` y `reservar` expresan el dominio.
- **Responsabilidad única:** dominio valida; `StockService` orquesta;
  repositorio persiste; FastAPI adapta HTTP.
- **Inversión de dependencias:** `StockService` depende del pequeño contrato
  `ProductoRepository` (Protocol), no de sqlite3. SQLite implementa ese contrato.
- **Separación:** API → Application → Domain; Infrastructure implementa Repository.
  El dominio no importa FastAPI, Pydantic ni SQLite.

El repositorio usa SQL parametrizado. Cada operación tiene una transacción SQLite
`BEGIN IMMEDIATE`, con commit o rollback y cierre de conexión. Esto serializa las
operaciones de este demo y evita sobrescribir reservas concurrentes. No se necesita
infraestructura adicional para esta carga pequeña.

No incluye frontend, autenticación ni API Management. El siguiente paso, previa
confirmación, será exponer este servicio junto con Orders mediante APIM.

## Docker

Requisito: Docker en ejecución y Docker Compose v2 o posterior con contenedores
Linux. No necesitas Python, FastAPI ni una instalación de SQLite en la PC.
Desde la carpeta `inventory-service`:

```bash
# Opcional: el valor por defecto de Compose ya es /data/inventory.db.
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs -f inventory-service
```

La imagen usa Python 3.14.7 slim y ejecuta
`python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`.
El puerto 8000 se publica en la PC. `INVENTORY_DB_PATH=/data/inventory.db` utiliza
la variable que ya tenía la aplicación, sin cambios de código. Si cambias el
nombre del archivo, mantenlo dentro de `/data` para conservar la persistencia.
El volumen `inventory-demo_inventory_data` se monta en `/data`.
SQLite es un archivo utilizado por Python, no un servidor ni un segundo contenedor.
El healthcheck consulta el OpenAPI existente mediante urllib de Python, sin
instalar curl ni añadir endpoints. Verifica respuesta HTTP, no una consulta SQL.

### Comprobar HTTP y persistencia en Docker

```bash
# El ID lo genera SQLite; usa el recibido en las siguientes consultas.
curl -i -X POST http://localhost:8000/productos \
  -H 'Content-Type: application/json' \
  -d '{"nombre":"Teclado","precio":4.50,"stockDisponible":10}'
curl -i http://localhost:8000/productos/1
curl -i -X POST http://localhost:8000/productos/1/reservar \
  -H 'Content-Type: application/json' -d '{"cantidad":2}'
# Esperado: 201, 200 y 200; stock final 8.

docker compose up -d --force-recreate inventory-service
# Espera a que aparezca healthy y consulta el mismo producto:
docker compose ps
curl -i http://localhost:8000/productos/1
# Debe conservar stock 8.
```

```bash
docker compose logs --tail=100 inventory-service
docker compose stop
docker compose start
docker compose down  # Conserva el volumen; NO añadir -v.
```

Copia el proyecto a PC2 sin `.venv`, bases locales ni `.env` personal y ejecuta
`docker compose up -d --build`. El volumen es local a cada PC y no se copia con el
código. Desde otra PC usa `http://IP_DE_PC2:8000/productos/1`, con conectividad y
puerto permitido en el firewall. No se han configurado HTTPS, AWS ni túneles.

La comprobación previa de HTTP y persistencia fue con FastAPI nativo, no Docker.
Las imágenes y los volúmenes Docker aún requieren validación en una PC con Docker
Engine: no está disponible en el entorno donde se prepararon estos archivos.

## GitHub Actions: CI y entrega continua

Repositorio privado: https://github.com/BryanSilva99/inventory-service.
El workflow `.github/workflows/inventory.yml` se ejecuta en pull requests a `main`,
push a `main` y manualmente desde Actions.

- **CI:** instala dependencias, ejecuta todas las pruebas, construye Docker y prueba
  creación, reserva, consulta y persistencia después de reiniciar el contenedor.
  Utiliza un volumen temporal independiente de los datos de la demo.
- **Entrega:** después de CI, los cambios de `main` publican exactamente la imagen
  probada en `ghcr.io/bryansilva99/inventory-service`, con etiquetas `latest` y el
  SHA completo del commit. Los pull requests no publican imágenes.
- La publicación usa el `GITHUB_TOKEN` automático con permiso `packages: write`;
  no requiere guardar un token personal en Secrets.

El despliegue automático a un servidor queda pendiente de definir el destino y
conectar su runner o sus credenciales. Publicar la imagen no actualiza por sí solo
el servicio que está ejecutándose en la PC de la demo.

Referencia: [publicar imágenes Docker con GitHub Actions](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images).

## Catálogo y precio de venta

Producto: `productoId` generado automáticamente, `nombre`, `precio`, `stockDisponible`.
`POST /productos` no acepta `productoId`; responde 201 con los cuatro campos.
GET individual, GET listado y reserva devuelven también precio como número JSON:

```json
[{"productoId":1,"nombre":"Coca Cola 500 ml","precio":4.50,"stockDisponible":20}]
```

El dominio utiliza `Decimal`; SQLite guarda `precio_centimos INTEGER` para evitar
la conversión a REAL que puede producir la afinidad NUMERIC de SQLite. El ID usa
`INTEGER PRIMARY KEY AUTOINCREMENT`, generado al insertar. Reservar conserva precio.
Solo el adaptador HTTP serializa el precio a número JSON; React envía un número a Java.

Crear producto → Inventory genera ID.
Nueva venta → React obtiene producto + precio de Inventory → usuario selecciona
cantidad → React envía productoId + cantidad + precioUnitario a Orders → Orders
conserva precioUnitario como precio histórico de la venta.

Inventory mantiene el precio actual del catálogo. Orders conserva el precio unitario aplicado en cada pedido.
Confirmar un pedido no reserva automáticamente stock.

## Base SQLite anterior sin precio

No existe un sistema de migraciones. Una tabla antigua vacía se recrea automáticamente.
Si contiene productos, el arranque falla con un mensaje explícito, sin alterar sus datos.
No se asignan precios ficticios. Para esta demo, respalda y recrea el catálogo con
precios reales. Detén Inventory antes de respaldar. Para la ruta local por defecto:

```bash
# Con Inventory detenido; conserva una copia consistente, incluidos datos WAL.
python - <<'PYCODE'
import sqlite3
from pathlib import Path
source = Path('data/inventory.db')
backup = Path('data/inventory-antes-precio.db')
if backup.exists():
    raise SystemExit('El respaldo ya existe: elige otra ruta')
with sqlite3.connect(source) as src, sqlite3.connect(backup) as dst:
    src.backup(dst)
PYCODE
# Arranca en un archivo nuevo; no borres la base anterior.
INVENTORY_DB_PATH="$PWD/data/inventory-con-precio.db" python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

En Docker, detén el servicio y cambia `INVENTORY_DB_PATH` en `.env` a
`/data/inventory-con-precio.db`; ejecuta `docker compose up -d --build`.
La base anterior permanece en el volumen. No uses `down -v`.
Los IDs de un catálogo recreado pueden coincidir con IDs antiguos de Orders:
revisa las asociaciones históricas antes de reutilizarlo en una demo con pedidos.
Si debes conservar esos vínculos, hace falta una migración manual con precios reales
y preservación de IDs; este cambio no la ejecuta.

El cambio conserva rutas y métodos. Una integración AWS API Gateway HTTP proxy
que pasa JSON no necesita cambios; si hay modelos de validación o plantillas de
mapeo configurados, actualízalos manualmente al nuevo contrato. No se modificó AWS.
