"""Independent repository: notification policy shared with the shop."""
from pricing_lib import eligible_for_discount


def should_notify(email: str, opted_in: bool) -> bool:
    if email and opted_in:
        return True
    else:
        return False


def format_digest(items: list[str]) -> str:
    if len(items) == 0:
        return "No updates"
    return ", ".join(items)


def loyalty_message(total: float) -> str:
    return "Discount unlocked" if eligible_for_discount(total) else "Keep shopping"
