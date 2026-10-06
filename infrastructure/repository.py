import sqlite3
from decimal import Decimal
from dataclasses import replace
from contextlib import contextmanager, closing
from pathlib import Path
from domain.producto_stock import ProductoStock


def inicializar_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(productos_stock)")}
        if columns and "precio_centimos" not in columns:
            if connection.execute("SELECT COUNT(*) FROM productos_stock").fetchone()[0]:
                raise RuntimeError("SQLite antigua sin precios: respalda la base y recréala siguiendo README.md. No se modificaron tus productos.")
            connection.execute("DROP TABLE productos_stock")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS productos_stock (
                producto_id INTEGER PRIMARY KEY AUTOINCREMENT,
                precio_centimos INTEGER NOT NULL CHECK(precio_centimos > 0),
                nombre TEXT NOT NULL,
                stock_disponible INTEGER NOT NULL CHECK(stock_disponible >= 0)
            )
        """)


class SQLiteProductoRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def buscar_por_id(self, producto_id: int) -> ProductoStock | None:
        row = self.connection.execute(
            "SELECT producto_id, nombre, precio_centimos, stock_disponible FROM productos_stock WHERE producto_id = ?",
            (producto_id,),
        ).fetchone()
        return self._producto(row) if row else None

    def listar(self) -> list[ProductoStock]:
        rows = self.connection.execute(
            "SELECT producto_id, nombre, precio_centimos, stock_disponible FROM productos_stock"
        ).fetchall()
        return [self._producto(row) for row in rows]

    @staticmethod
    def _producto(row):
        return ProductoStock(row[0], row[1], Decimal(row[2]) / 100, row[3])

    def crear(self, producto: ProductoStock) -> ProductoStock:
        if producto.producto_id is not None:
            raise ValueError("La persistencia genera el productoId")
        cursor = self.connection.execute(
            "INSERT INTO productos_stock (nombre, precio_centimos, stock_disponible) VALUES (?, ?, ?)",
            (producto.nombre, int(producto.precio * 100), producto.stock_disponible),
        )
        return replace(producto, producto_id=cursor.lastrowid)

    def guardar(self, producto: ProductoStock):
        if producto.producto_id is None:
            raise ValueError("El producto debe estar creado antes de actualizarlo")
        self.connection.execute(
            "UPDATE productos_stock SET nombre = ?, precio_centimos = ?, stock_disponible = ? WHERE producto_id = ?",
            (producto.nombre, int(producto.precio * 100), producto.stock_disponible, producto.producto_id),
        )


@contextmanager
def abrir_repository(db_path: Path):
    connection = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    try:
        # Una transacción por operación evita perder reservas concurrentes.
        connection.execute("BEGIN IMMEDIATE")
        yield SQLiteProductoRepository(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
