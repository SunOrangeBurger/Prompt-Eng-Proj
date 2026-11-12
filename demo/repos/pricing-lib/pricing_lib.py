"""Pretend independent repo: small pricing policy."""


def eligible_for_discount(total: float) -> bool:
    if total >= 100:
        return True
    else:
        return False


def final_price(total: float, discount: float) -> float:
    if eligible_for_discount(total):
        return total * (1 - discount / 100)
    return total
