"""Money helpers. All BDT amounts are rounded HALF_UP to 2 decimal places."""
from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal("0.01")


def round_money(value) -> Decimal:
    """Round a value to 2 dp using ROUND_HALF_UP. Never raises on None -> 0."""
    if value is None:
        return Decimal("0.00")
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def as_decimal(value) -> Decimal:
    """Coerce a value to Decimal safely (None/empty -> 0)."""
    if value is None or value == "":
        return Decimal("0")
    return Decimal(value)


def percent_of(amount, percent) -> Decimal:
    """amount * percent / 100, rounded to 2 dp."""
    amount = as_decimal(amount)
    percent = as_decimal(percent)
    return round_money(amount * percent / Decimal("100"))


def discount_percentage(old_price, new_price) -> int:
    """Whole-number % discount between two prices, or 0 if not applicable."""
    old_price = as_decimal(old_price)
    new_price = as_decimal(new_price)
    if old_price <= 0 or new_price >= old_price:
        return 0
    pct = (old_price - new_price) / old_price * Decimal("100")
    return int(pct.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
