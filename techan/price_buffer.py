from dataclasses import dataclass
from collections import deque

@dataclass
class PriceBuffer:
    symbol: str
    period: int


    def __post_init__(self):
        self.prices = deque(maxlen=self.period) 

    def add_price(self, price: float):
        self.prices.append(price)

    def get_prices(self):
        return list(self.prices)
    
    def get_average_price(self):
        if len(self.prices) == 0:
            return 0.0
        return sum(self.prices) / len(self.prices)


    def get_std_dev(self):
        if len(self.prices) == 0:
            return 0.0
        avg = self.get_average_price()
        variance = sum((p - avg) ** 2 for p in self.prices) / len(self.prices)
        return variance ** 0.5

    @property
    def is_full(self):
        return len(self.prices) == self.period
