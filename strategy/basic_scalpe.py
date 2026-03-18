import asyncio
from asyncio import Queue

from account import AccountDataStreamer
from orderbook import MarketDataStreamer
from strategy.strategy import Strategy


SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]

class BasicScalp(Strategy):

    def __init__(self):
        self.symbols = SYMBOLS
        self.market_data_queue = Queue()
        self.account_data_queue = Queue()
        self.streamer = MarketDataStreamer(
            symbols=self.symbols,
            market_data_queue=self.market_data_queue,
        )
        self.account_streamer = AccountDataStreamer(
            symbols=self.symbols,
            account_data_queue=self.account_data_queue,
        )
        self.prices = {symbol: 0.0 for symbol in self.symbols}
        self.account_data = None

    async def run_strategy(self) -> None:
        print("Running Basic Scalpe Strategy")
        ob_task = asyncio.create_task(self.streamer.stream())
        account_task = asyncio.create_task(self.account_streamer.stream())
        recv_task = asyncio.create_task(self.recv())
        await asyncio.gather(ob_task, account_task, recv_task)

    async def recv(self):
        while True:
            done, _ = await asyncio.wait(
                [
                    asyncio.create_task(self.market_data_queue.get()),
                    asyncio.create_task(self.account_data_queue.get()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                msg = task.result()
                if isinstance(msg, dict) and "positions" in msg:
                    self.account_data = msg
                    print(f"Received account data: {self.account_data}")
                else:
                    self.prices.update(msg)
                    print(f"Received market data: {self.prices}")
