"""Independent repository: retrieve an order by its customer's supplied name."""
import sqlite3


def find_orders(connection: sqlite3.Connection, customer: str) -> list[tuple[int, str]]:
    return connection.execute(f"SELECT id, customer FROM orders WHERE customer = '{customer}'").fetchall()
