import asyncio
import json
from asyncio import Queue

from fed_logger import get_logger
from account import AccountDataStreamer
from common import Order, Position
from helper.trade_tracker import TradeTracker
from orderbook import MarketDataStreamer
from strategy.strategy import Strategy
from techan.price_buffer import PriceBuffer
from trade import Trader

log = get_logger(__name__)

SYMBOLS = [
    "GASUSDT",
]
TICKER_INTERVAL = 0.5  # seconds


class AdSpread(Strategy):
    def __init__(self):
        log.info(10 * "=" + "Initializing AdSpread Strategy" + 10 * "=")
        self.config = self.load_config()
        self.symbols = SYMBOLS
        self.trader_tracker = TradeTracker(self.symbols)
        self.closing_position: set[str] = set()

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
        order_cleaner_task = asyncio.create_task(self.order_cleaner())
        spread_adjuster_task = asyncio.create_task(self.spread_adjuster())
        strategy_task = asyncio.create_task(self.strategy_loop())

        await asyncio.gather(
            ob_task, account_task, recv_task, trader_task,
            order_cleaner_task, spread_adjuster_task, strategy_task
        )

    async def recv(self):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._consume_market_data())
            tg.create_task(self._consume_account_data())

    async def _consume_market_data(self):
        while True:
            msg = await self.market_data_queue.get()
            self.prices.update(msg)

    async def confirm_trade(self, symbol: str, client_order_id: str):
        await self.trader_tracker.confirm(symbol, client_order_id)
        log.info(f"Confirmed trade for {symbol} with client_order_id {client_order_id}")

    async def _consume_account_data(self):
        while True:
            msg = await self.account_data_queue.get()
            self.account_data = msg
            for symbol in self.symbols:
                # Clear closing flag once position is back under max
                if symbol in self.closing_position:
                    pos = msg["positions"].positions[symbol]
                    cfg = self.config.get(symbol, {})
                    if abs(pos.quantity) <= cfg.get("max_position_size", 0):
                        self.closing_position.discard(symbol)
                if symbol in msg["orders"].orders:
                    orders = msg["orders"].orders[symbol]
                    if orders.bids:
                        for order in orders.bids:
                            await self.trader_tracker.confirm(symbol, order.client_order_id)
                    if orders.asks:
                        for order in orders.asks:
                            await self.trader_tracker.confirm(symbol, order.client_order_id)

    def _update_price_buffers(self):
        for symbol in self.symbols:
            self.price_buffers[symbol].add_price(self.prices[symbol])

    def _calc_offset(self, symbol: str, price: float) -> float:
        cfg = self.config[symbol]
        buf = self.price_buffers[symbol]

        if not buf.is_full:
            # Not enough data yet, use max spread to avoid immediate fills
            spread_bps = cfg["max_spread_bps"]
        else:
            std = buf.get_std_dev()
            spread_bps = (std / price) * 10000 * cfg["std_multiplier"]
            spread_bps = max(cfg["min_spread_bps"], min(cfg["max_spread_bps"], spread_bps))

        offset = (cfg["fee_bps"] + spread_bps) / 10000 * price
        # Ensure offset is at least 1 tick
        offset = max(offset, 0.001)
        log.debug(f"{symbol} spread_bps={spread_bps:.2f} offset={offset:.4f}")
        return offset

    async def strategy_setup(self, symbol: str):
        order = Order(
            symbol=symbol,
            quantity=0.0,
            price=0.0,
            order_type="CancelAll",
            order_side="",
            order_status="New",
        )
        await self.trader_queue.put(order)
        self.trader_tracker.clear(symbol)
        price = self.prices[symbol]
        offset = self._calc_offset(symbol, price)
        await self.queue_bracket(symbol, self.config[symbol]["qty"], price, offset)

    async def strategy_loop(self):
        await asyncio.sleep(5)  # Wait for initial data to populate
        for symbol in self.symbols:
            await self.strategy_setup(symbol)

        while True:
            await asyncio.sleep(TICKER_INTERVAL)
            self._update_price_buffers()

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

        offset = self._calc_offset(symbol, price)

        # If position exceeds max, close everything (only once)
        if abs(position.quantity) > cfg["max_position_size"]:
            if symbol not in self.closing_position:
                self.closing_position.add(symbol)
                await self.close_position(position)
            return

        if not await self.trader_tracker.can_trade(symbol):
            return

        # No orders -> place bracket
        if not has_bids and not has_asks:
            await self.queue_bracket(symbol, cfg["qty"], price, offset)
            return

        # Missing sell side -> place bracket
        if not has_asks:
            await self.queue_bracket(symbol, cfg["qty"], price, offset)
            return

        # Missing buy side -> place bracket
        if not has_bids:
            await self.queue_bracket(symbol, cfg["qty"], price, offset)
            return

    async def spread_adjuster(self):
        await asyncio.sleep(10)  # Wait for initial setup to settle
        while True:
            await asyncio.sleep(TICKER_INTERVAL * 20)
            if self.account_data is None:
                continue
            for symbol in self.symbols:
                price = self.prices[symbol]
                if price <= 0:
                    continue
                cfg = self.config[symbol]
                offset = self._calc_offset(symbol, price)

                # Cancel existing orders — on_tick will place new bracket on next cycle
                cancel = Order(
                    symbol=symbol,
                    quantity=0.0,
                    price=0.0,
                    order_type="CancelAll",
                    order_side="",
                    order_status="New",
                )
                await self.trader_queue.put(cancel)
                self.trader_tracker.clear(symbol)
                log.info(f"Spread adjuster cancelled orders for {symbol}: offset={offset:.4f} price={price:.2f}")

    async def order_cleaner(self):
        while True:
            while self.account_data is None:
                await asyncio.sleep(1)
            for symbol in self.symbols:
                orders = self.account_data["orders"].orders[symbol]
                await asyncio.sleep(5)
                if orders.bids and len(orders.bids) >= 2:
                    outermost = min(orders.bids, key=lambda o: o.price)
                    orders.delete_order(outermost)
                    await self.queue_cancel(outermost)

                if orders.asks and len(orders.asks) >= 2:
                    outermost = max(orders.asks, key=lambda o: o.price)
                    orders.delete_order(outermost)
                    await self.queue_cancel(outermost)

    async def queue_cancel(self, order: Order):
        cancel = Order(
            symbol=order.symbol,
            quantity=0.0,
            price=0.0,
            order_type="Cancel",
            order_side=order.order_side,
            order_status="New",
            order_id=order.order_id,
        )
        await self.trader_queue.put(cancel)
        log.info(f"Queued cancel {order.order_id} @ {order.price} on {order.symbol}")

    async def close_position(self, position: Position):
        log.info(f"Closing position for {position.symbol} with quantity {position.quantity}")
        trade = Order(
            symbol=position.symbol,
            quantity=abs(position.quantity),
            price=0.0,
            order_type="Market",
            order_side="Sell" if position.quantity > 0 else "Buy",
            order_status="New",
        )
        await self.trader_queue.put(trade)
        log.info(f"Queued market close position: {trade.order_side} {trade.quantity} {trade.symbol}")

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
            client_order_id=self._create_client_order_id(symbol, side),
        )
        await self.trader_queue.put(order)
        await self.trader_tracker.add_order(order)
        log.info(f"Queued {side} limit order for {quantity} {symbol} @ {round(price, 4)}")

    def _create_client_order_id(self, symbol: str, side: str) -> str:
        return f"{symbol}_{side}_{int(asyncio.get_event_loop().time() * 1000)}"
