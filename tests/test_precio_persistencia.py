import sqlite3
import unittest
from contextlib import closing
from decimal import Decimal
from fastapi.testclient import TestClient
from domain.producto_stock import ProductoStock
from infrastructure.repository import inicializar_db, abrir_repository
from tests import test_listar_productos
from api.main import app


class PrecioPersistenciaTest(unittest.TestCase):
    setUp = test_listar_productos.ListarProductosTest.setUp

    def test_flujo_http_y_persistencia(self):
        with TestClient(app) as client:
            body = {"nombre": "Coca Cola 500 ml", "precio": 4.50, "stockDisponible": 20}
            first = client.post('/productos', json=body)
            second = client.post('/productos', json=body)
            self.assertEqual(first.status_code, 201)
            producto = first.json()
            self.assertGreater(producto['productoId'], 0)
            self.assertNotEqual(producto['productoId'], second.json()['productoId'])
            self.assertIsInstance(producto['precio'], (int, float))
            path = f"/productos/{producto['productoId']}"
            self.assertEqual(client.get(path).json(), producto)
            self.assertIn(producto, client.get('/productos').json())
            reserved = client.post(path + '/reservar', json={'cantidad': 2})
            self.assertEqual(reserved.status_code, 200)
            self.assertEqual(reserved.json()['precio'], 4.5)
            self.assertEqual(reserved.json()['stockDisponible'], 18)
            self.assertEqual(client.post(path + '/reservar', json={'cantidad': 19}).status_code, 409)
            for cantidad in (0, -1):
                self.assertEqual(client.post(path + '/reservar', json={'cantidad': cantidad}).status_code, 400)
        with abrir_repository(self.db_path) as repository:
            saved = repository.buscar_por_id(producto['productoId'])
            self.assertEqual((saved.producto_id, saved.nombre, saved.precio, saved.stock_disponible),
                             (producto['productoId'], body['nombre'], Decimal('4.50'), 18))
        with TestClient(app) as client:
            self.assertEqual(client.get(path).json(), reserved.json())

    def test_http_datos_invalidos(self):
        body = {'nombre': 'Producto', 'precio': 4.5, 'stockDisponible': 20}
        with TestClient(app) as client:
            for changes in ({'precio': 0}, {'precio': -1}, {'precio': '4.50'}, {'precio': None},
                            {'precio': True}, {'precio': 'NaN'}, {'precio': 1.001}, {'nombre': '  '},
                            {'stockDisponible': -1}, {'productoId': 100}):
                with self.subTest(changes=changes):
                    self.assertIn(client.post('/productos', json={**body, **changes}).status_code, (400, 422))
            del body['precio']
            self.assertEqual(client.post('/productos', json=body).status_code, 422)

    def test_dominio_precio_invalido(self):
        for price in (Decimal('NaN'), Decimal('Infinity'), Decimal('-Infinity'), Decimal('0'),
                      Decimal('-1'), Decimal('1.001'), 'invalido', 4.5):
            with self.subTest(price=price), self.assertRaises(ValueError):
                ProductoStock(None, 'Producto', price, 1)

    def test_base_antigua_no_se_modifica(self):
        legacy = self.db_path.parent / 'legacy.db'
        with closing(sqlite3.connect(legacy)) as connection, connection:
            connection.execute('CREATE TABLE productos_stock (producto_id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, stock_disponible INTEGER NOT NULL)')
            connection.execute("INSERT INTO productos_stock VALUES (100, 'Antiguo', 20)")
        with self.assertRaisesRegex(RuntimeError, 'respalda'):
            inicializar_db(legacy)
        with closing(sqlite3.connect(legacy)) as connection, connection:
            self.assertEqual(connection.execute('SELECT * FROM productos_stock').fetchall(), [(100, 'Antiguo', 20)])

    def test_base_antigua_vacia_se_actualiza(self):
        legacy = self.db_path.parent / 'empty.db'
        with closing(sqlite3.connect(legacy)) as connection, connection:
            connection.execute('CREATE TABLE productos_stock (producto_id INTEGER PRIMARY KEY, nombre TEXT, stock_disponible INTEGER)')
        inicializar_db(legacy)
        with abrir_repository(legacy) as repository:
            result = repository.crear(ProductoStock(None, 'Nuevo', Decimal('0.10'), 1))
        with abrir_repository(legacy) as repository:
            self.assertEqual(repository.buscar_por_id(result.producto_id).precio, Decimal('0.10'))
