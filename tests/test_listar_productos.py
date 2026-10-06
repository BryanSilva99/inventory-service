import tempfile
from decimal import Decimal
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.main import app
from application.stock_service import StockService
from infrastructure.repository import abrir_repository, inicializar_db


class ListarProductosTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = Path(self.directory.name) / "inventory.db"
        inicializar_db(self.db_path)
        self.patch = patch("api.main.DB_PATH", self.db_path)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_listar_sin_productos(self):
        with TestClient(app) as client:
            response = client.get("/productos")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_listar_todos_con_mismo_modelo_que_consulta_individual(self):
        with abrir_repository(self.db_path) as repository:
            service = StockService(repository)
            service.crear("Producto AWS", Decimal("4.50"), 8)
            service.crear("Sin stock", Decimal("1.00"), 0)
        with TestClient(app) as client:
            response = client.get("/productos")
            individuales = [client.get(f"/productos/{id}").json() for id in (1, 2)]
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json(), individuales)
