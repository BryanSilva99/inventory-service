import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from fastapi import Depends, FastAPI, Path as ApiPath, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from application.stock_service import StockService, ProductoNoEncontrado, ProductoDuplicado
from domain.producto_stock import ProductoStock, StockInsuficiente
from infrastructure.repository import abrir_repository, inicializar_db

DB_PATH = Path(os.environ.get("INVENTORY_DB_PATH", str(Path(__file__).resolve().parents[1] / "data/inventory.db")))


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_db(DB_PATH)
    yield


app = FastAPI(title="Inventory Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key"],
)


class CrearProductoRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    productoId: int = Field(le=9223372036854775807)
    nombre: str
    stockDisponible: int = Field(le=9223372036854775807)


class ReservaRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    cantidad: int


class ProductoResponse(BaseModel):
    productoId: int
    nombre: str
    stockDisponible: int

    @classmethod
    def desde(cls, producto: ProductoStock):
        return cls(productoId=producto.producto_id, nombre=producto.nombre,
                   stockDisponible=producto.stock_disponible)


def stock_service():
    with abrir_repository(DB_PATH) as repository:
        yield StockService(repository)


Service = Annotated[StockService, Depends(stock_service, scope="function")]
ProductoId = Annotated[int, ApiPath(gt=0, le=9223372036854775807)]


@app.exception_handler(ProductoNoEncontrado)
async def no_encontrado(request: Request, exc: ProductoNoEncontrado):
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(ProductoDuplicado)
@app.exception_handler(StockInsuficiente)
async def conflicto(request: Request, exc: Exception):
    return JSONResponse(status_code=409, content={"error": str(exc)})


@app.exception_handler(ValueError)
async def datos_invalidos(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.post("/productos", response_model=ProductoResponse, status_code=201)
def crear(body: CrearProductoRequest, service: Service):
    return ProductoResponse.desde(service.crear(body.productoId, body.nombre, body.stockDisponible))


@app.get("/productos", response_model=list[ProductoResponse])
def listar(service: Service):
    return [ProductoResponse.desde(producto) for producto in service.listar()]


@app.get("/productos/{producto_id}", response_model=ProductoResponse)
def consultar(producto_id: ProductoId, service: Service):
    return ProductoResponse.desde(service.consultar(producto_id))


@app.post("/productos/{producto_id}/reservar", response_model=ProductoResponse)
def reservar(producto_id: ProductoId, body: ReservaRequest, service: Service):
    return ProductoResponse.desde(service.reservar(producto_id, body.cantidad))
