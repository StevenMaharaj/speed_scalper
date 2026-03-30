from common import Order


class TradeTracker:
    def __init__(self, symbols: list[str]):
        self.pending: dict[str, set[str]] = {symbol: set() for symbol in symbols}

    def add(self, symbol: str, client_order_id: str):
        self.pending[symbol].add(client_order_id)

    async def add_order(self, order: Order):
        self.pending[order.symbol].add(order.client_order_id)

    async def confirm(self, symbol: str, client_order_id: str):
        self.pending[symbol].discard(client_order_id)

    def clear(self, symbol: str):
        self.pending[symbol].clear()

    async def can_trade(self, symbol: str) -> bool:
        return len(self.pending[symbol]) == 0
