import unittest
from domain.producto_stock import ProductoStock, StockInsuficiente


class ProductoStockTest(unittest.TestCase):
    def test_crear_producto_valido(self):
        producto = ProductoStock(1, "Teclado", 10)
        self.assertEqual((producto.producto_id, producto.nombre, producto.stock_disponible),
                         (1, "Teclado", 10))

    def test_impedir_stock_negativo(self):
        with self.assertRaises(ValueError):
            ProductoStock(1, "Teclado", -1)

    def test_reservar_disminuye_stock(self):
        producto = ProductoStock(1, "Teclado", 10)
        producto.reservar(2)
        self.assertEqual(producto.stock_disponible, 8)

    def test_impedir_reserva_mayor_al_stock(self):
        producto = ProductoStock(1, "Teclado", 10)
        with self.assertRaises(StockInsuficiente):
            producto.reservar(11)
        self.assertEqual(producto.stock_disponible, 10)

    def test_impedir_cantidad_no_positiva(self):
        for cantidad in (0, -1):
            with self.subTest(cantidad=cantidad), self.assertRaises(ValueError):
                ProductoStock(1, "Teclado", 10).reservar(cantidad)

    def test_impedir_id_y_nombre_invalidos(self):
        for producto_id, nombre in ((0, "Teclado"), (1, "  ")):
            with self.subTest(producto_id=producto_id, nombre=nombre), self.assertRaises(ValueError):
                ProductoStock(producto_id, nombre, 10)
