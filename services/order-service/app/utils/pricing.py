from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple
from app.core.config import settings


def round_currency(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_order_totals(
    items_with_quantities: List[Tuple[Decimal, int]],
) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    item_total = Decimal("0.00")
    for unit_price, quantity in items_with_quantities:
        item_total += Decimal(str(unit_price)) * Decimal(quantity)

    item_total = round_currency(item_total)

    tax_percent = Decimal(str(settings.TAX_PERCENTAGE))
    tax_amount = round_currency((item_total * tax_percent) / Decimal("100.0"))

    free_threshold = Decimal(str(settings.FREE_DELIVERY_THRESHOLD))
    if item_total >= free_threshold:
        delivery_fee = Decimal("0.00")
    else:
        delivery_fee = round_currency(Decimal(str(settings.DEFAULT_DELIVERY_FEE)))

    grand_total = round_currency(item_total + tax_amount + delivery_fee)
    return item_total, tax_amount, delivery_fee, grand_total
