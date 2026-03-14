from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    symbol: str
    quantity: float
    price: float
    order_type: str  # "Market" or "Limit"
    order_side: str  # "Buy" or "Sell"
    order_status: str  # "New", "Filled", "Partially Filled", "Cancelled", etc.


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float
    avg_price: float
    current_price: float

    def unrealized_pnl(self) -> float:
        if self.side == "Long":
            return (self.current_price - self.avg_price) * self.quantity
        else:  # Short
            return (self.avg_price - self.current_price) * self.quantity

    def add_position(self, quantity: float, price: float):
        total_cost = self.avg_price * self.quantity + price * quantity
        self.quantity += quantity
        self.avg_price = total_cost / self.quantity

    @property
    def side(self) -> str:
        return "Long" if self.quantity > 0 else "Short"
