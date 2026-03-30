import asyncio
import os
from asyncio import Queue

from dotenv import load_dotenv
from pybit.exceptions import InvalidRequestError
from pybit.unified_trading import HTTP

from common import Order
from fed_logger import get_logger

log = get_logger(__name__)

CATEGORY = "linear"


class Trader:
    def __init__(self, trade_queue: Queue):
        self.trade_queue = trade_queue
        api_key, api_secret = self._load_api_credentials()
        self.session = HTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
        )

    def _load_api_credentials(self):
        load_dotenv()
        return os.getenv("BYBIT_1_KEY"), os.getenv("BYBIT_1_SECRET")

    async def run(self):
        while True:
            order: Order = await self.trade_queue.get()
            log.info(f"Received trade signal: {order}")

            if order.order_type == "Market":
                self.market_order(order)
            elif order.order_type == "Limit":
                self.limit_order(order)
            elif order.order_type == "Cancel":
                self.cancel_order(order)
            elif order.order_type == "CancelAll":
                self.cancel_all_orders(order)
            else:
                log.warning(f"Unknown order type: {order.order_type}")

    def market_order(self, order: Order):
        if order.order_type != "Market":
            log.warning(f"Invalid order type for market order: {order.order_type}")
            return
        try:
            result = self.session.place_order(
                category=CATEGORY,
                symbol=order.symbol,
                side=order.order_side,
                orderType="Market",
                qty=str(order.quantity),
            )
            log.info(f"Market order result: {result}")
            return result
        except Exception as e:
            log.warning(f"Market order failed: {e}")
            return None

    def limit_order(self, order: Order):
        if order.order_type != "Limit":
            log.warning(f"Invalid order type for limit order: {order.order_type}")
            return
        try:
            result = self.session.place_order(
                category=CATEGORY,
                symbol=order.symbol,
                side=order.order_side,
                orderType="Limit",
                qty=str(order.quantity),
                price=str(order.price),
                orderLinkId=order.client_order_id,
            )
            log.info(f"Limit order result: {result}")
            return result
        except Exception as e:
            log.warning(f"Limit order failed: {e}")
            return None

    def cancel_order(self, order: Order):
        try:
            result = self.session.cancel_order(
                category=CATEGORY,
                symbol=order.symbol,
                orderId=order.order_id,
            )
            log.info(f"Cancel order result: {result}")
            return result
        except InvalidRequestError as e:
            log.warning(f"Cancel order failed (order may already be gone): {e}")
            return None

    def cancel_all_orders(self, order: Order):
        try:
            result = self.session.cancel_all_orders(
                category=CATEGORY,
                symbol=order.symbol,
            )
            log.info(f"Cancel all orders result: {result}")
            return result
        except Exception as e:
            log.warning(f"Cancel all orders failed: {e}")
            return None


async def produce_trade(market_data_queue: Queue):
    order = Order(
        symbol="BTCUSDT",
        quantity=0.001,
        price=69900.0,
        order_type="Limit",
        order_side="Buy",
        order_status="New",
    )
    await asyncio.sleep(1)  # Simulate some delay before producing the trade signal
    await market_data_queue.put(order)
    await asyncio.sleep(5)  # Simulate some delay
    # Cancel All Orders
    cancel_all_order = Order(
        symbol="BTCUSDT",
        quantity=0.0,
        price=0.0,
        order_type="CancelAll",
        order_side="",
        order_status="New",
    )
    await market_data_queue.put(cancel_all_order)
    # print(f"Produced trade signal: {order}")
    # Here you can implement logic to process the market data, such as generating trade signals


async def main():
    queue = Queue()
    trader = Trader(trade_queue=queue)
    await asyncio.gather(
        trader.run(),
        produce_trade(queue),
    )


if __name__ == "__main__":
    asyncio.run(main())
