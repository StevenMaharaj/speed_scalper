from asyncio import Queue

from .common import Position


class AccountDataStreamer:
    def __init__(self, symbols: list[str], account_data_queue: Queue):
        self.account_data_queue = account_data_queue
        self.account_data = {
            "positions:": {
                symbol: Position(
                    symbol=symbol,
                    quantity=0.0,
                    avg_price=0.0,
                    current_price=0.0,
                )
                for symbol in symbols
            },
            "orders": {
                symbol: [] for symbol in symbols
            },

        }
