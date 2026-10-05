from typing import Protocol
from domain.producto_stock import ProductoStock


class ProductoRepository(Protocol):
    def buscar_por_id(self, producto_id: int) -> ProductoStock | None: ...
    def guardar(self, producto: ProductoStock) -> None: ...
    def listar(self) -> list[ProductoStock]: ...


class ProductoNoEncontrado(Exception):
    pass


class ProductoDuplicado(Exception):
    pass


class StockService:
    def __init__(self, repository: ProductoRepository):
        self.repository = repository

    def crear(self, producto_id: int, nombre: str, stock_disponible: int) -> ProductoStock:
        producto = ProductoStock(producto_id, nombre, stock_disponible)
        if self.repository.buscar_por_id(producto_id) is not None:
            raise ProductoDuplicado("El producto ya existe")
        self.repository.guardar(producto)
        return producto

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
