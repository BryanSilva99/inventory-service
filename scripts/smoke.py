"""Prueba HTTP sobre el contenedor efímero de CI, nunca sobre la base de la demo."""

import json
import os
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("INVENTORY_SMOKE_URL", "http://127.0.0.1:8000")


def request(path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = Request(BASE_URL + path, data=body, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=3) as response:
        return response.status, json.load(response)


def main():
    mode = sys.argv[1]
    if mode not in ("create", "verify"):
        raise ValueError("Usar create o verify")
    for attempt in range(45):
        try:
            request("/openapi.json")
            break
        except (URLError, TimeoutError, ConnectionError):
            time.sleep(2)
    else:
        raise RuntimeError("La API no inició en 90 segundos")
    if mode == "create":
        status, _ = request("/productos", {"productoId": 1, "nombre": "CI", "stockDisponible": 10})
        assert status == 201
        status, product = request("/productos/1/reservar", {"cantidad": 2})
        assert status == 200 and product["stockDisponible"] == 8
    status, product = request("/productos/1")
    assert status == 200 and product["stockDisponible"] == 8
    status, products = request("/productos")
    assert status == 200 and product in products
    print(f"Smoke {mode}: API correcta, stock persistido = 8")


if __name__ == "__main__":
    main()
