import sqlite3
from contextlib import contextmanager
from pathlib import Path
from domain.producto_stock import ProductoStock


def inicializar_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS productos_stock (
                producto_id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                stock_disponible INTEGER NOT NULL CHECK(stock_disponible >= 0)
            )
        """)
    connection.close()


class SQLiteProductoRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def buscar_por_id(self, producto_id: int) -> ProductoStock | None:
        row = self.connection.execute(
            "SELECT producto_id, nombre, stock_disponible FROM productos_stock WHERE producto_id = ?",
            (producto_id,),
        ).fetchone()
        return ProductoStock(*row) if row else None

    def listar(self) -> list[ProductoStock]:
        rows = self.connection.execute(
            "SELECT producto_id, nombre, stock_disponible FROM productos_stock"
        ).fetchall()
        return [ProductoStock(*row) for row in rows]

    def guardar(self, producto: ProductoStock):
        self.connection.execute("""
            INSERT INTO productos_stock (producto_id, nombre, stock_disponible)
            VALUES (?, ?, ?)
            ON CONFLICT(producto_id) DO UPDATE SET
                nombre = excluded.nombre, stock_disponible = excluded.stock_disponible
        """, (producto.producto_id, producto.nombre, producto.stock_disponible))


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
