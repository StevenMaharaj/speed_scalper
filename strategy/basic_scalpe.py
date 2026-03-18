import asyncio
from asyncio import Queue

from orderbook import MarketDataStreamer
from strategy.strategy import Strategy


SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]

class BasicScalp(Strategy):

    def __init__(self):
        self.symbols = SYMBOLS
        self.market_data_queue = Queue()
        self.streamer = MarketDataStreamer(
            symbols=self.symbols,
            market_data_queue=self.market_data_queue,
        )
        self.prices = {symbol: 0.0 for symbol in self.symbols}

    async def run_strategy(self) -> None:
        print("Running Basic Scalpe Strategy")
        # self.make_connection()
        ob_task = asyncio.create_task(self.streamer.stream())
        recv_task = asyncio.create_task(self.recv())
        await asyncio.gather(ob_task, recv_task)
        

    def make_connection(self):
        asyncio.create_task(self.streamer.stream())

    async def recv(self):
        while True:
            done, _ = await asyncio.wait(
                [asyncio.create_task(self.market_data_queue.get())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                msg = task.result()
                self.prices.update(msg)
                print(f"Received market data: {self.prices}")
