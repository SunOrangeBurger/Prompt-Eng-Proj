"""Pretend downstream repo importing both shared libraries."""
from pricing_lib import final_price
from settings_lib import parse_settings


def checkout(total: float, settings: str) -> float:
    config = parse_settings(settings)
    discount = config.get("discount", 0)
    if not isinstance(discount, (float, int)):
        raise ValueError("Discount must be numeric")
    return final_price(total, discount)
