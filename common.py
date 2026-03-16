from dataclasses import dataclass


@dataclass
class Order:
    symbol: str
    quantity: float
    price: float
    order_type: str  # "Market" or "Limit"
    order_side: str  # "Buy" or "Sell"
    order_status: str  # "New", "Filled", "Partially Filled", "Cancelled", etc.


@dataclass
class Orders:
    symbol: str
    bids: list[Order] | None = None
    asks: list[Order] | None = None

    def add_order(self, order: Order):
        if self.bids is None:
            self.bids = []
        if self.asks is None:
            self.asks = []
        if order.order_side == "Buy":
            self.bids.append(order)
        else:
            self.asks.append(order)

    def delete_order(self, order: Order):
        if self.bids is None:
            raise ValueError("Bids list is not initialized")
        if self.asks is None:
            raise ValueError("Asks list is not initialized")
        if order.order_side == "Buy":
            self.bids = [o for o in self.bids if o != order]
        else:
            self.asks = [o for o in self.asks if o != order]

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
        self.quantity = round(self.quantity, 8)  # Round to avoid floating-point issues
        self.avg_price = round(self.avg_price, 8)

    def update_current_price(self, price: float):
        self.current_price = price

    @property
    def side(self) -> str:
        return "Long" if self.quantity > 0 else "Short"



