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
# Crear: 201. Utiliza otro ID si el producto ya existe.
curl -i -X POST http://127.0.0.1:8000/productos \
  -H 'Content-Type: application/json' \
  -d '{"productoId":1,"nombre":"Teclado","stockDisponible":10}'

# Consultar: 200, stock 10
curl -i http://127.0.0.1:8000/productos/1

# Reservar: 200, stock 8
curl -i -X POST http://127.0.0.1:8000/productos/1/reservar \
  -H 'Content-Type: application/json' -d '{"cantidad":2}'
```

Producto inexistente: 404. Stock insuficiente o producto duplicado: 409.
Datos inválidos de dominio: 400. JSON o tipos inválidos: 422.
Los campos numéricos del body deben ser enteros, no cadenas ni decimales.
Los identificadores y el stock persistido tienen el límite técnico de los enteros
SQLite de 64 bits; se valida en la entrada HTTP.

## Pruebas

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m pip check
```

Ocho pruebas verifican creación, ID/nombre válidos, stock no negativo,
reserva válida, stock insuficiente, cantidades no positivas y listado HTTP.
También se verificaron los tres endpoints con un servidor real y una base temporal:
crear con stock 10, reservar 2, comprobar SQLite y reiniciar conservando stock 8.
La verificación no deja productos de prueba en la base de desarrollo.

## DDD y SOLID para la sustentación

- **Bounded Context:** Inventario tiene modelo y base propios.
- **Aggregate Root:** `ProductoStock` es la entrada a las reglas de su stock;
  `reservar()` controla los cambios. Sus campos no admiten asignación directa normal.
- **Invariantes:** ID positivo, nombre no vacío, stock entero no negativo,
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
# Elige un ID nuevo si ya tienes productos en este volumen.
curl -i -X POST http://localhost:8000/productos \
  -H 'Content-Type: application/json' \
  -d '{"productoId":1,"nombre":"Teclado","stockDisponible":10}'
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

- **CI:** instala dependencias, ejecuta las ocho pruebas, construye Docker y prueba
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
