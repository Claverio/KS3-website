from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PurchasePrice:
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    service_fee: Decimal
    total: Decimal


def calculate_purchase_price(project, quantity):
    if quantity < 1:
        raise ValueError("Slot quantity must be at least one.")
    unit_price = Decimal(project.slot_price)
    subtotal = unit_price * quantity
    service_fee = Decimal(project.service_fee)
    return PurchasePrice(unit_price, quantity, subtotal, service_fee, subtotal + service_fee)
