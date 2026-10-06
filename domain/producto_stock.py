from dataclasses import dataclass
from decimal import Decimal


class StockInsuficiente(ValueError):
    pass


@dataclass(frozen=True)
class ProductoStock:
    producto_id: int | None
    nombre: str
    precio: Decimal
    stock_disponible: int

    def __post_init__(self):
        if self.producto_id is not None and (type(self.producto_id) is not int or self.producto_id <= 0):
            raise ValueError("El productoId debe ser un entero positivo")
        if not isinstance(self.precio, Decimal) or not self.precio.is_finite() or self.precio <= 0:
            raise ValueError("El precio debe ser un decimal finito mayor que cero")
        if self.precio > Decimal("9999999999.99") or self.precio != self.precio.quantize(Decimal("0.01")):
            raise ValueError("El precio admite hasta dos decimales y un máximo de 9999999999.99")
        if not isinstance(self.nombre, str) or not self.nombre.strip():
            raise ValueError("El nombre no puede estar vacío")
        if type(self.stock_disponible) is not int or self.stock_disponible < 0:
            raise ValueError("El stock debe ser un entero no negativo")

    def reservar(self, cantidad: int):
        if type(cantidad) is not int or cantidad <= 0:
            raise ValueError("La cantidad debe ser un entero positivo")
        if cantidad > self.stock_disponible:
            raise StockInsuficiente("Stock insuficiente")
        object.__setattr__(self, "stock_disponible", self.stock_disponible - cantidad)
