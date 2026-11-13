"""Pretend downstream repo importing both shared libraries."""
from pricing_lib import final_price
from settings_lib import parse_settings
from records_lib import find_orders
from documents_lib import read_invoice
from notifications_lib import format_digest, should_notify
import sqlite3


def checkout(total: float, settings: str) -> float:
    config = parse_settings(settings)
    discount = config.get("discount", 0)
    if not isinstance(discount, (float, int)):
        raise ValueError("Discount must be numeric")
    return final_price(total, discount)


def customer_summary(connection: sqlite3.Connection, customer: str) -> str:
    return format_digest([f"Order {order_id}" for order_id, _ in find_orders(connection, customer)])


def invoice_preview(root: str, filename: str) -> str:
    return read_invoice(root, filename).strip()


def notification_label(email: str, opted_in: bool) -> str:
    return "Send" if should_notify(email, opted_in) else "Skip"
