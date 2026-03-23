import asyncio
import json
from asyncio import Queue

from account import AccountDataStreamer
from orderbook import MarketDataStreamer
from strategy.strategy import Strategy

SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]


class BasicScalp(Strategy):
    def __init__(self):
        self.config = self.load_config()
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

    def load_config(self) -> dict:
        with open("./config/basic_scalper.json", "r") as f:
            return json.load(f)

    async def run_strategy(self) -> None:
        print("Running Basic Scalpe Strategy")
        ob_task = asyncio.create_task(self.streamer.stream())
        account_task = asyncio.create_task(self.account_streamer.stream())
        recv_task = asyncio.create_task(self.recv())
        strategy_task = asyncio.create_task(self.strategy_loop())
        await asyncio.gather(ob_task, account_task, recv_task, strategy_task)

    async def recv(self):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._consume_market_data())
            tg.create_task(self._consume_account_data())

    async def _consume_market_data(self):
        while True:
            msg = await self.market_data_queue.get()
            self.prices.update(msg)

    async def _consume_account_data(self):
        while True:
            msg = await self.account_data_queue.get()
            self.account_data = msg

    async def strategy_loop(self):
        await asyncio.sleep(5)  # Wait for initial data to populate
        while True:
            await asyncio.sleep(2)
            print(f"Current prices: {self.prices}")
            print(f"Account data: {self.account_data}")
