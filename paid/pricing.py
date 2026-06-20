from decimal import Decimal, ROUND_HALF_UP


PRICE_INR_499 = "INR_499"
PRICE_INR_1 = "INR_1"
PRICE_INR_0 = "INR_0"

PRICE_CHOICES = [
    (PRICE_INR_499, "₹499"),
    # Temporarily hidden. Re-enable when these price points are needed again.
    # ("INR_100", "₹100"),
    # ("INR_20", "₹20"),
    (PRICE_INR_1, "₹1"),
    (PRICE_INR_0, "₹0"),
]

PRICE_MAP = {
    PRICE_INR_499: 49900,
    PRICE_INR_1: 100,
    PRICE_INR_0: 0,
}

COMPANY_COMPONENT_PAISE = 25000
DOCTOR_COMPONENT_PAISE = 24900


def _clean_discount_percent(discount_percent) -> Decimal:
    if discount_percent in (None, ""):
        return Decimal("0")
    percent = Decimal(str(discount_percent))
    if percent < 0:
        return Decimal("0")
    if percent > 100:
        return Decimal("100")
    return percent


def calculate_order_amounts(price_variant: str, discount_percent=None) -> tuple[int, int, int]:
    base_amount = PRICE_MAP[price_variant]
    if price_variant != PRICE_INR_499:
        return base_amount, 0, base_amount

    percent = _clean_discount_percent(discount_percent)
    discount = (Decimal(DOCTOR_COMPONENT_PAISE) * percent / Decimal("100")).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    discount_paise = int(discount)
    final_amount = COMPANY_COMPONENT_PAISE + max(0, DOCTOR_COMPONENT_PAISE - discount_paise)
    return base_amount, discount_paise, final_amount


def revenue_split_amounts(order, amount_paise: int) -> tuple[int, int]:
    if getattr(order, "price_variant", "") == PRICE_INR_499:
        company_amount = min(COMPANY_COMPONENT_PAISE, amount_paise)
        return company_amount, max(0, amount_paise - company_amount)

    company_amount = int(amount_paise / 2)
    return company_amount, amount_paise - company_amount
