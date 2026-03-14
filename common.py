from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    symbol: str
    quantity: int # in dollars
    price: float
    order_type: str # "Market" or "Limit"
    order_side: str # "Buy" or "Sell"
