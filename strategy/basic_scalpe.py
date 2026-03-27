import asyncio
import json
from asyncio import Queue

from account import AccountDataStreamer
from common import Order, Position
from orderbook import MarketDataStreamer
from strategy.strategy import Strategy
from techan.price_buffer import PriceBuffer
from trade import Trader

SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]


class BasicScalp(Strategy):
    def __init__(self):
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
        with open("./config/basic_scalper.json", "r") as f:
            return json.load(f)

    async def run_strategy(self) -> None:
        print("Running Basic Scalpe Strategy")
        ob_task = asyncio.create_task(self.streamer.stream())
        account_task = asyncio.create_task(self.account_streamer.stream())
        trader_task = asyncio.create_task(self.trader.run())
        recv_task = asyncio.create_task(self.recv())
        strategy_task = asyncio.create_task(self.strategy_loop())
        await asyncio.gather(
            ob_task, account_task, recv_task, trader_task, strategy_task
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

    async def strategy_loop(self):
        await asyncio.sleep(5)  # Wait for initial data to populate
        while True:
            await asyncio.sleep(1)
            self._update_price_buffers()

            print(f"Current prices: {self.prices}")
            print(f"Account data: {self.account_data}")

            for symbol in self.symbols:
                await self.on_tick(symbol)

    async def on_tick(self, symbol: str):
        if self.account_data is None:
            return
        if symbol not in self.config:
            return

        cfg = self.config[symbol]
        price = self.prices[symbol]
        if price <= 0:
            return

        position = self.account_data["positions"].positions[symbol]
        orders = self.account_data["orders"].orders[symbol]
        has_bids = orders.bids is not None and len(orders.bids) > 0
        has_asks = orders.asks is not None and len(orders.asks) > 0
        has_position = position.quantity != 0

        offset = (cfg["fee_bps"] + cfg["bps"] * 3) / 10000 * price

        # If position exceeds max, close everything
        if abs(position.quantity) > cfg["max_position_size"]:
            await self.close_position(position)
            return

        # No orders, no position -> place bracket
        if not has_bids and not has_asks and not has_position:
            buy = Order(
                symbol=symbol,
                quantity=cfg["qty"],
                price=round(price - offset, 2),
                order_type="Limit",
                order_side="Buy",
                order_status="New",
            )
            sell = Order(
                symbol=symbol,
                quantity=cfg["qty"],
                price=round(price + offset, 2),
                order_type="Limit",
                order_side="Sell",
                order_status="New",
            )
            await self.trader_queue.put(buy)
            await self.trader_queue.put(sell)
            return

        # BUY filled (long position), no sell order -> place sell
        if position.quantity > 0 and not has_asks:
            sell = Order(
                symbol=symbol,
                quantity=cfg["qty"],
                price=round(price + offset, 2),
                order_type="Limit",
                order_side="Sell",
                order_status="New",
            )
            await self.trader_queue.put(sell)
            return

        # SELL filled (short position), no buy order -> place buy
        if position.quantity < 0 and not has_bids:
            buy = Order(
                symbol=symbol,
                quantity=cfg["qty"],
                price=round(price - offset, 2),
                order_type="Limit",
                order_side="Buy",
                order_status="New",
            )
            await self.trader_queue.put(buy)
            return

    async def close_position(self, position: Position):
        # Implement logic to close the position, e.g., by placing a market order in the opposite direction
        print(
            f"Closing position for {position.symbol} with quantity {position.quantity}"
        )
        # Here you would create an Order object and put it in the trader_queue to execute the trader_task
        trade = Order(
            symbol=position.symbol,
            quantity=abs(position.quantity),  # Example quantity to close
            price=0.0,  # Market order
            order_type="Market",
            order_side="Sell" if position.quantity > 0 else "Buy",
            order_status="New",
        )
        await self.trader_queue.put(trade)
