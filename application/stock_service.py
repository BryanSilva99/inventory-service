from typing import Protocol
from decimal import Decimal
from domain.producto_stock import ProductoStock


class ProductoRepository(Protocol):
    def buscar_por_id(self, producto_id: int) -> ProductoStock | None: ...
    def crear(self, producto: ProductoStock) -> ProductoStock: ...
    def guardar(self, producto: ProductoStock) -> None: ...
    def listar(self) -> list[ProductoStock]: ...


class ProductoNoEncontrado(Exception):
    pass


class StockService:
    def __init__(self, repository: ProductoRepository):
        self.repository = repository

    def crear(self, nombre: str, precio: Decimal, stock_disponible: int) -> ProductoStock:
        producto = ProductoStock(None, nombre, precio, stock_disponible)
        return self.repository.crear(producto)

    def consultar(self, producto_id: int) -> ProductoStock:
        producto = self.repository.buscar_por_id(producto_id)
        if producto is None:
            raise ProductoNoEncontrado("Producto no encontrado")
        return producto

    def listar(self) -> list[ProductoStock]:
        return self.repository.listar()

    def reservar(self, producto_id: int, cantidad: int) -> ProductoStock:
        producto = self.consultar(producto_id)
        producto.reservar(cantidad)
        self.repository.guardar(producto)
        return producto
