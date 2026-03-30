import asyncio
import json
from asyncio import Queue

from fed_logger import get_logger
from account import AccountDataStreamer
from common import Order
from orderbook import MarketDataStreamer
from strategy.strategy import Strategy
from techan.price_buffer import PriceBuffer
from trade import Trader

log = get_logger(__name__)

SYMBOLS = [
    "GASUSDT",
]
TICKER_INTERVAL = 0.5


class AdSpread2(Strategy):
    def __init__(self):
        log.info(10 * "=" + "Initializing AdSpread2 Strategy" + 10 * "=")
        self.config = self.load_config()
        self.symbols = SYMBOLS

        self.market_data_queue = Queue()
        self.account_data_queue = Queue()
        self.trader_queue = Queue()
        self.streamer = MarketDataStreamer(
            symbols=self.symbols,
            market_data_queue=self.market_data_queue,
        )
        self.account_streamer = AccountDataStreamer(
            symbols=self.symbols,
            account_data_queue=self.account_data_queue,
        )
        self.trader = Trader(trade_queue=self.trader_queue)
        self.prices = {symbol: 0.0 for symbol in self.symbols}
        self.price_buffers = {
            symbol: PriceBuffer(symbol, 50) for symbol in self.symbols
        }
        self.account_data = None

    def load_config(self) -> dict:
        with open("./config/adspread.json", "r") as f:
            return json.load(f)

    async def run_strategy(self) -> None:
        ob_task = asyncio.create_task(self.streamer.stream())
        account_task = asyncio.create_task(self.account_streamer.stream())
        trader_task = asyncio.create_task(self.trader.run())
        recv_task = asyncio.create_task(self.recv())
        spread_adjuster_task = asyncio.create_task(self.spread_adjuster())
        strategy_task = asyncio.create_task(self.strategy_loop())

        await asyncio.gather(
            ob_task, account_task, recv_task, trader_task,
            spread_adjuster_task, strategy_task
        )

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

    def _update_price_buffers(self):
        for symbol in self.symbols:
            self.price_buffers[symbol].add_price(self.prices[symbol])

    def _calc_offset(self, symbol: str, price: float) -> float:
        cfg = self.config[symbol]
        buf = self.price_buffers[symbol]

        if not buf.is_full:
            spread_bps = cfg["max_spread_bps"]
        else:
            std = buf.get_std_dev()
            spread_bps = (std / price) * 10000 * cfg["std_multiplier"]
            spread_bps = max(cfg["min_spread_bps"], min(cfg["max_spread_bps"], spread_bps))

        offset = (cfg["fee_bps"] + spread_bps) / 10000 * price
        offset = max(offset, 0.001)
        log.debug(f"{symbol} spread_bps={spread_bps:.2f} offset={offset:.4f}")
        return offset

    async def strategy_loop(self):
        await asyncio.sleep(5)
        for symbol in self.symbols:
            cfg = self.config[symbol]
            price = self.prices[symbol]
            offset = self._calc_offset(symbol, price)
            await self.queue_bracket(symbol, cfg["qty"], price, offset)

        while True:
            await asyncio.sleep(TICKER_INTERVAL)
            self._update_price_buffers()
            for symbol in self.symbols:
                await self.on_tick(symbol)

    async def on_tick(self, symbol: str):
        if self.account_data is None:
            log.debug(f"{symbol} on_tick: account_data is None")
            return
        if symbol not in self.config:
            return

        price = self.prices[symbol]
        if price <= 0:
            return

        orders = self.account_data["orders"].orders[symbol]
        has_bids = orders.bids is not None and len(orders.bids) > 0
        has_asks = orders.asks is not None and len(orders.asks) > 0

        log.debug(f"{symbol} on_tick: has_bids={has_bids} has_asks={has_asks}")

        if not has_bids and not has_asks:
            log.info(f"No existing orders for {symbol}, placing new brackets")
            cfg = self.config[symbol]
            offset = self._calc_offset(symbol, price)
            await self.queue_bracket(symbol, cfg["qty"], price, offset)

    async def spread_adjuster(self):
        await asyncio.sleep(10)
        while True:
            await asyncio.sleep(TICKER_INTERVAL * 20)
            for symbol in self.symbols:
                cancel = Order(
                    symbol=symbol,
                    quantity=0.0,
                    price=0.0,
                    order_type="CancelAll",
                    order_side="",
                    order_status="New",
                )
                await self.trader_queue.put(cancel)
                # Reset local order state since exchange orders are gone
                if self.account_data is not None:
                    orders = self.account_data["orders"].orders[symbol]
                    orders.bids = []
                    orders.asks = []
                log.info(f"Spread adjuster cancelled orders for {symbol}")

    async def queue_bracket(self, symbol: str, quantity: float, price: float, offset: float):
        await self.queue_limit_order(symbol, quantity, price - offset, "Buy")
        await self.queue_limit_order(symbol, quantity, price + offset, "Sell")

    async def queue_limit_order(self, symbol: str, quantity: float, price: float, side: str):
        order = Order(
            symbol=symbol,
            quantity=quantity,
            price=round(price, 4),
            order_type="Limit",
            order_side=side,
            order_status="New",
        )
        await self.trader_queue.put(order)
        log.info(f"Queued {side} limit order for {quantity} {symbol} @ {round(price, 4)}")
